import datetime
import glob
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
        raise Exception('Unrecognized ticket duration', ticket_duration_str)
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


def plot(df, date, write_file=True, small=True):
    # Get trace for a given date
    trace = get_trace(df, date)
    if len(trace) == 0:
        return ""
    series = to_pandas_series(trace)

    if small:
        ax = series.plot(figsize=(2.5, 1.7))
    else:
        ax = series.plot()

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

    if write_file:

        out_dir = "out"
        day_dir = date.strftime('%Y/%m/%d')
        if small:
            filename = "{}/{}/plot.png".format(out_dir, day_dir)
        else:
            filename = "{}/{}/plot_large.png".format(out_dir, day_dir)
        with open_file(filename, "wb") as figfile:
            # pad_inches will remove padding around the image
            plt.savefig(figfile, format="png", bbox_inches="tight", pad_inches=0)
            plt.close()

        return '<img src="{}"/>'.format(filename)


def month_plots(df, file_name, date_range):

    with open(file_name, 'w') as f:
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

        first = date_range[0]
        if first.weekday() > 0:
            f.write("<td>{}</td>".format(first.strftime('%d/%m/%Y')))
            for _ in range(first.weekday()):
                f.write("<td/>\n")

        for d in date_range:
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


if __name__ == "__main__":
    df = pd.read_csv("data/processed/processed.csv", parse_dates=["Date"], dayfirst=True)
    # df = pd.read_pickle("data/processed/processed.pickle")

    # filter out unknown durations
    df = df[df["duration"].isin(["1 Hour", "2 Hour", "4 Hour", "All Day"])]

    # sort by date (there are two ticket machines, so input isn't chronological)
    df = df.sort_values(by=["Date"])

    # df.to_pickle("data/processed/processed.pickle")

    # for month_start in pd.date_range(pd.Timestamp(2017, 9, 1), pd.Timestamp(2019, 5, 1), freq='MS'): # MS is month start
    #     print(month_start)
    #     month_plots(df, "new/{}.html".format(month_start.strftime('%Y_%m')), pd.date_range(month_start, month_start + pd.DateOffset(months=1), closed='left'))

    for month_start in pd.date_range(pd.Timestamp(2021, 1, 1), pd.Timestamp(2023, 8, 1), freq='MS'): # MS is month start
        print(month_start)
        month_plots(df, "{}.html".format(month_start.strftime('%Y_%m')), pd.date_range(month_start, month_start + pd.DateOffset(months=1), closed='left'))
