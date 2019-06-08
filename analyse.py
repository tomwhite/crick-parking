import datetime
import matplotlib.pyplot as plt
import pandas as pd
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
    return traces.TimeSeries.merge(per_car_timeseries, operation=sum, compact=True)


# Load data
df = pd.read_csv("~/Downloads/Transaction Report 010119 to 310519.csv", parse_dates=["Date"])

# filter out overnight
df = df[~df['Tariff'].isin(['105DA', '105M', '105U'])]

# add ticket duration
df['duration'] = df['Description.1'].str.extract('(1 Hour|2 Hour|4 Hour|All Day)', expand=True)

# sort by date (there are two ticket machines)
df = df.sort_values(by=["Date"])

# Show ticket duration counts
x = df.groupby(['duration']).size().reset_index(name='counts')
print(x)


# Get trace for a given date
trace = get_trace(df, pd.Timestamp(2019, 2, 1))

dist = trace.distribution(normalized=False)
print("mean", dist.mean())
print("max", dist.max())

trace = get_trace(df, pd.Timestamp(2019, 2, 2))

dist = trace.distribution(normalized=False)
print("mean", dist.mean())
print("max", dist.max())

range = pd.date_range(pd.Timestamp(2019, 2, 1), pd.Timestamp(2019, 3, 1))
print(range)

series = to_pandas_series(trace)
series.plot()
plt.show()

# TODO
# turn x into pandas series and then plot DONE
# pull out ticket duration DONE
# find day with max
# what is average occupancy over opening times?
