import numpy as np
import matplotlib as mpl
mpl.use('Agg')  # Headless mode
import matplotlib.pyplot as plt

results = []
with open('top500.txt') as top500:
    results = [int(l.strip()) for l in top500.readlines()]

# some fake data
# evaluate the histogram
values, base = np.histogram(results, bins=100000)

# evaluate the cumulative
cumulative = np.cumsum(values, dtype="float32")
cumulative /= np.max(cumulative)

# plot the cumulative function
plt.xscale('log')
plt.xlabel('Response size (Bytes)')
plt.title('CDF of HTTP response sizes for top 500 sites')
plt.plot(base[:-1], cumulative, c='blue')

m1 = 3 * 1500
plt.plot((m1, m1), (0, 1), 'k-')
m1 = 10 * 1500
plt.plot((m1, m1), (0, 1), 'k-')
plt.savefig('results/' + 'top500' + '.png')