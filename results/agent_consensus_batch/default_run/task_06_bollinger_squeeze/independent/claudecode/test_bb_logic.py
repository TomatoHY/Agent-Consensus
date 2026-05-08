import numpy as np

# Test the Bollinger Band calculation logic
test_prices = [10.0, 10.1, 10.2, 10.15, 10.18, 10.2, 10.22, 10.21, 10.19, 10.2,
               10.21, 10.22, 10.23, 10.24, 10.25, 10.26, 10.27, 10.28, 10.29, 10.3]

# Calculate Bollinger Bands
middle_band = np.mean(test_prices)
std_dev = np.std(test_prices, ddof=1)
upper_band = middle_band + 2 * std_dev
lower_band = middle_band - 2 * std_dev

bb_width = (upper_band - lower_band) / middle_band

print(f"Test data (consolidation scenario):")
print(f"Middle band: {middle_band:.4f}")
print(f"Upper band: {upper_band:.4f}")
print(f"Lower band: {lower_band:.4f}")
print(f"BB Width: {bb_width:.4f} ({bb_width*100:.2f}%)")
print(f"Is consolidation (< 5%): {bb_width < 0.05}")

# Test with volatile prices
volatile_prices = [10.0, 12.0, 9.0, 13.0, 8.0, 14.0, 7.0, 15.0, 6.0, 16.0,
                   5.0, 17.0, 4.0, 18.0, 3.0, 19.0, 2.0, 20.0, 1.0, 21.0]

middle_band2 = np.mean(volatile_prices)
std_dev2 = np.std(volatile_prices, ddof=1)
upper_band2 = middle_band2 + 2 * std_dev2
lower_band2 = middle_band2 - 2 * std_dev2

bb_width2 = (upper_band2 - lower_band2) / middle_band2

print(f"\nTest data (volatile scenario):")
print(f"Middle band: {middle_band2:.4f}")
print(f"Upper band: {upper_band2:.4f}")
print(f"Lower band: {lower_band2:.4f}")
print(f"BB Width: {bb_width2:.4f} ({bb_width2*100:.2f}%)")
print(f"Is consolidation (< 5%): {bb_width2 < 0.05}")
