import datetime
import matplotlib.pyplot as plt
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

# Find the date on which the max occupancy occurred
r = pd.date_range(pd.Timestamp(2019, 1, 1), pd.Timestamp(2019, 5, 10))
date_of_max = max(r, key=lambda date: max_for_date(df, date))
print(date_of_max, max_for_date(df, date_of_max))

# Get trace for a given date
trace = get_trace(df, interesting_date)
series = to_pandas_series(trace)
ax = series.plot()

# # Find number of ticket sales in midday 30 min slot
# for date in r:
#     rolling = get_rolling(df, date)
#     print(date, get_tickets_in_window(rolling, date))

# Get rolling counts for a given date and plot on same figure
rolling = get_rolling(df, interesting_date)
rolling.plot(ax=ax, secondary_y=True)

plt.show()
