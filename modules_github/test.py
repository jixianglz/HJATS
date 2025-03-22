import matplotlib.pyplot as plt
x = [1, 2, 3, 4, 5]
y = [2, 4, 6, 8, 10]

# Create separate lists for the red and green segments
x_red = [x[i] for i in range(len(x)) if i%2==0]
y_red = [y[i] for i in range(len(y)) if i%2==0]
x_green = [x[i] for i in range(len(x)) if i%2!=0]
y_green = [y[i] for i in range(len(y)) if i%2!=0]

# Plot the red segments
plt.plot(x_red, y_red, color='red')

# Plot the green segments
plt.plot(x_green, y_green, color='green')

# Show the plot
plt.show()