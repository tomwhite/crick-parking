import datetime
import matplotlib.pyplot as plt
import os
import pandas as pd
import seaborn as sns
import traces


def get_ticket_end(ticket_start, ticket_duration_str):
    if ticket_duration_str == '1 Hour':
        ticket_end = ticket_start + pd.Timedelta(hours=1)
    elif ticket_duration_str == '2 Hour':
        ticket_end = ticket_start + pd.Timedelta(hours=2)
    elif ticket_duration_str == '4 Hour':
        ticket_end = ticket_start + pd.Timedelta(hours=4)
    elif ticket_duration_str == 'All Day':
        ticket_end = ticket_start.replace(hour=18, minute=0)
    else:
        return None
    ticket_end_of_day = ticket_start.replace(hour=18, minute=0)
    if ticket_end > ticket_end_of_day:
        ticket_end = ticket_end_of_day
    return ticket_end


def to_pandas_series(trace):
    interpolated = trace.sample(
        sampling_period=datetime.timedelta(minutes=1),
        interpolate="previous"
    )
    timestamps, data = list(zip(*interpolated))
    idx = pd.DatetimeIndex(timestamps)
    return pd.Series(data, idx)


def get_trace(df, date):
    end_date = date + pd.Timedelta(days=1)
    single_date_df = df[(df['Date'] >= date) & (df['Date'] < end_date)]
    per_car_timeseries = []
    for x in single_date_df[["Date", "duration"]].values:
        ts = traces.TimeSeries(default=0)
        ticket_start = x[0]
        ticket_end = get_ticket_end(ticket_start, x[1])
        ts[ticket_start], ts[ticket_end] = 1, 0
        per_car_timeseries.append(ts)
    ret = traces.TimeSeries.merge(per_car_timeseries, operation=sum, compact=True)
    return ret


def max_for_date(df, date):
    trace = get_trace(df, date)
    if len(trace) == 0:
        print("No data for ", date)
        return 0
    return trace.distribution(normalized=False).max()


def get_rolling(df, date, window='30T'):
    end_date = date + pd.Timedelta(days=1)
    single_date_df = df[(df['Date'] >= date) & (df['Date'] < end_date)]
    # restrict to Date field
    events = single_date_df[["Date"]]
    events['x'] = 1
    # resample every minute
    events = events.resample('1T', on='Date').sum()
    # calculate rolling counts
    return events.rolling(window).sum()


def get_tickets_in_window(rolling, date, hour=12):
    return rolling.loc[date + pd.Timedelta(hours=hour)].iloc[0]


def open_file(filename, mode="r"):
    if filename.startswith("gs://"):
        fs = gcsfs.GCSFileSystem(token="google_default")
        return fs.open(filename, mode)
    else:
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        return open(filename, mode)


def plot(df, date):
    # Get trace for a given date
    trace = get_trace(df, date)
    if len(trace) == 0:
        return ""
    series = to_pandas_series(trace)
    ax = series.plot(figsize=(2.5, 1.7))

    # Make axes consistent
    ax.set_ylim(0, 170)

    # Get rolling counts for a given date and plot on same figure
    rolling = get_rolling(df, date)
    ax2 = rolling.plot(ax=ax, secondary_y=True)

    ax.set_xlim(date + pd.Timedelta(hours=7), date + pd.Timedelta(hours=18))
    ax2.set_ylim(0, 40)

    # TODO: fix hour labels
    # See https://stackoverflow.com/questions/33743394/matplotlib-dateformatter-for-axis-label-not-working
    # from matplotlib.dates import HourLocator, DateFormatter
    # ax2.xaxis.set_major_locator(HourLocator(interval=2)) # tick every two hours
    # ax2.xaxis.set_major_formatter(DateFormatter('%H'))

    # Remove unnecessary labels
    ax.get_legend().remove()
    ax.xaxis.set_label_text("")

    out_dir = "out"
    day_dir = date.strftime('%Y/%m/%d')
    filename = "{}/{}/plot.png".format(out_dir, day_dir)
    with open_file(filename, "wb") as figfile:
        # pad_inches will remove padding around the image
        plt.savefig(figfile, format="png", bbox_inches="tight", pad_inches=0)
        plt.close()

    return '<img src="{}"/>'.format(filename)


# Load data
df = pd.read_csv("~/Downloads/Transaction Report 010119 to 310519.csv", parse_dates=["Date"], dayfirst=True)

# filter out overnight
df = df[~df['Tariff'].isin(['105DA', '105M', '105U'])]

# add ticket duration
df['duration'] = df['Description.1'].str.extract('(1 Hour|2 Hour|4 Hour|All Day)', expand=True)

# sort by date (there are two ticket machines, so input isn't chronological)
df = df.sort_values(by=["Date"])

# Show ticket duration counts
x = df.groupby(['duration']).size().reset_index(name='counts')
print(x)

# print(df)
#
# print(df.info())
#
# df['hour'] = df['Date'].apply(lambda x: x.hour)
#
# print(df)
#
# #sns.distplot(df['hour'], hist=True, kde=False, bins=24, hist_kws={'edgecolor':'black'})
#
# sns.countplot(x="hour", data=df)
#
# plt.show()
#
# import sys
# sys.exit(1)

# Interesting dates
interesting_date = pd.Timestamp(2019, 2, 10) # Sunday; filled up v quickly, then sales stopped suddenly
interesting_date = pd.Timestamp(2019, 5, 4) # max capacity
interesting_date = pd.Timestamp(2019, 4, 4) # boring Thursday in April

# # Find the date on which the max occupancy occurred
# r = pd.date_range(pd.Timestamp(2019, 1, 1), pd.Timestamp(2019, 5, 10))
# date_of_max = max(r, key=lambda date: max_for_date(df, date))
# print(date_of_max, max_for_date(df, date_of_max))

# # Find number of ticket sales in midday 30 min slot
# for date in r:
#     rolling = get_rolling(df, date)
#     print(date, get_tickets_in_window(rolling, date))

r = pd.date_range(pd.Timestamp(2019, 4, 1), pd.Timestamp(2019, 4, 30))

with open("index.html", 'w') as f:
    f.write("""<html>
    <head>
    <title>Crick Car Park Usage</title>
        <style>
            body {
                font-family: DejaVuSans, sans-serif;
            }
            th {
                font-weight: normal;
                text-align: center;
            }
        </style>
    </head>
    <body>
    <table>
        <tr>
            <th></th>
            <th>Monday</th>
            <th>Tuesday</th>
            <th>Wednesday</th>
            <th>Thursday</th>
            <th>Friday</th>
            <th>Saturday</th>
            <th>Sunday</th>
        </tr>
    <tr>
    """)

    if r[0].weekday() > 0:
        f.write("<td>{}</td>".format(r[0].strftime('%d/%m/%Y')))
        for _ in range(r[0].weekday()):
            f.write("<td/>\n")

    for d in r:
        if d.weekday() == 0:
            f.write("<td>{}</td>".format(d.strftime('%d/%m/%Y')))
        img = plot(df, d)
        f.write("<td>{}</td>\n".format(img))
        if d.weekday() == 6:
            f.write("</tr>\n")

    if d.weekday() != 6:
        f.write("</tr>\n")
    f.write("""
    </table>
    </body>
    </html>
    """)


#plt.show()
