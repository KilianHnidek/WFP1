from io import BytesIO
import base64

import mysql.connector
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import RobustScaler
from flask import Flask, request, Response, jsonify
from flask_cors import CORS
from prometheus_client import generate_latest, Counter, REGISTRY
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout, BatchNormalization
from tensorflow.keras.optimizers import SGD
from tensorflow.keras.regularizers import l2


app = Flask(__name__)
CORS(app, resources={r"/predictor/*": {"origins": "*"}})

# Define your metrics
REQUESTS = Counter('hello_worlds_total', 'Hello Worlds requested.')


@app.route('/predictor/hello')
def hello():
    REQUESTS.inc()  # increment counter
    return "Hello World!"


@app.route('/predictor/metrics', methods=['GET'])
def metrics():
    return Response(generate_latest(REGISTRY), mimetype='text/plain')


@app.route("/predictor/predict", methods=["GET", "POST"])
def predict():
    figures = predict_price()

    # Create a list to store the utf8 encoded figures
    encoded_figures = []

    # Convert each figure to utf8 and append to the list
    for fig in figures:
        # Save the figure to a BytesIO object
        buf = BytesIO()
        fig.savefig(buf, format='svg')
        buf.seek(0)
        plt.close(fig)  # Close to avoid memory leaks

        # Encode the figure as utf8
        svg = buf.getvalue().decode('utf-8')
        encoded_figures.append(svg)

    # Return the JSON response with the encoded figures
    return jsonify(figures=encoded_figures), 200


def predict_price():
    # connect to db
    conn = mysql.connector.connect(
        host='db',
        port=3306,
        user='root',
        password='root',
        database='scraperdb'
    )

    # create cursor
    cursor = conn.cursor()
    data = None
    try:
        # get data from both tables of the db
        cursor.execute("""
            SELECT scraperdb.hotels.hotelname, scraperdb.hotels.address, scraperdb.prices.price, 
            scraperdb.prices.scrapdate, scraperdb.prices.startdate,
            scraperdb.prices.enddate, scraperdb.prices.guests, scraperdb.prices.score, scraperdb.prices.reviewCount
            FROM scraperdb.hotels
            INNER JOIN scraperdb.prices ON scraperdb.hotels.hotelname = scraperdb.prices.hotelname
            ORDER BY scraperdb.hotels.hotelname
        """)

        # fetch data from db to variable data
        data = cursor.fetchall()
        print(data)
    except mysql.connector.Error as err:
        print("Error: {}".format(err))
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

    data = pd.DataFrame(data, columns=['Hotel Name', 'Address', 'Price', 'Scrap Date', 'Start Date', 'End Date',
                                       'Guests', 'Score', 'Review Count'])

    data['Price'] = data['Price'].str.replace(',', '').astype(float)

    data['Score'] = data['Score'].replace('', np.nan)
    data['Score'].fillna(data['Score'].str.replace(',', '').astype(float).mean(), inplace=True)
    data['Score'] = data['Score'].str.replace(',', '').astype(float)

    data['Review Count'] = data['Review Count'].astype(str).replace('', np.nan)
    data['Review Count'] = data['Review Count'].str.replace(',', '').astype(float)

    data['District'] = data['Address'].str.extract(r'(\d{1,2})\.', expand=False)

    data.dropna(subset=['District'], inplace=True)
    data['District'] = data['District'].astype('int64')
    data = data.drop_duplicates(subset=['Hotel Name'])

    hotels_per_district = data.groupby('District').size()

    # Calculate the number of nights based on start and end date
    data['Start Date'] = pd.to_datetime(data['Start Date'])
    data['End Date'] = pd.to_datetime(data['End Date'])
    data['Nights'] = (data['End Date'] - data['Start Date']).dt.days

    data.dropna(subset=['Price', 'District', 'Score', 'Review Count', 'Nights', 'Guests'], inplace=True)

    X = data[['District', 'Score', 'Review Count', 'Nights', 'Guests']]
    y = data['Price']

    scaler = RobustScaler()
    X_scaled = scaler.fit_transform(X)

    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.6, random_state=42)

    model = Sequential()

    # Input layer
    model.add(Dense(256, activation='relu', kernel_regularizer=l2(0.01), input_dim=X_train.shape[1]))
    model.add(BatchNormalization())
    model.add(Dropout(0.5))

    # Hidden layer 1
    model.add(Dense(128, activation='relu', kernel_regularizer=l2(0.01)))
    model.add(BatchNormalization())
    model.add(Dropout(0.5))

    # Hidden layer 2
    model.add(Dense(64, activation='relu', kernel_regularizer=l2(0.01)))
    model.add(BatchNormalization())
    model.add(Dropout(0.5))

    # Hidden layer 3
    model.add(Dense(32, activation='relu', kernel_regularizer=l2(0.01)))
    model.add(BatchNormalization())
    model.add(Dropout(0.5))

    # Output layer
    model.add(Dense(1, activation='sigmoid'))

    # Compile the model
    model.compile(optimizer=SGD(learning_rate=0.01, momentum=0.9, nesterov=True), loss='mean_squared_error')

    model.fit(X_train, y_train, epochs=200, batch_size=32, verbose=1)

    # Make predictions
    y_pred = model.predict(X_test)

    mse = mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    print('Mean Squared Error:', mse)
    print('R-squared Score:', r2)

    districts = list(range(1, 24))
    feature_names = ['District', 'Score', 'Review Count', 'Nights', 'Guests']
    sample_data = pd.DataFrame([[district, 8.5, 200, 3, 2] for district in districts], columns=feature_names)

    sample_data_scaled = scaler.transform(sample_data)
    predicted_prices = model.predict(sample_data_scaled)

    # Create future scenarios
    future_data = create_future_scenarios(districts, data)
    X_future_scaled = scaler.transform(future_data[['District', 'Score', 'Review Count', 'Nights', 'Guests']])
    predicted_future_prices = model.predict(X_future_scaled)

    district_figures = create_mean_price_trend_plot(data, model, scaler, future_data)

    fig1 = create_price_distribution_plot(data)
    fig2 = create_hotels_per_district_plot(hotels_per_district)
    fig3 = create_price_vs_score_plot(data)
    fig4 = create_predicted_prices_plot(districts, predicted_prices, scaler, X_future_scaled)
    fig5 = create_mean_price_trend_plot(data, model, scaler, future_data)
    figures = [fig1, fig2, fig3, fig4]
    figures.extend(fig5)

    return figures


def create_price_distribution_plot(data):
    fig, ax = plt.subplots()
    sns.histplot(data['Price'], bins=20, ax=ax)
    ax.set_title('Distribution of Prices')
    ax.set_xlabel('Price')
    ax.set_ylabel('Count')
    return fig


def create_hotels_per_district_plot(hotels_per_district):
    fig, ax = plt.subplots()
    sns.barplot(x=hotels_per_district.index, y=hotels_per_district.values, ax=ax)
    ax.set_xlabel("District")
    ax.set_ylabel("Number of Hotels")
    ax.set_title("Number of Hotels per District")
    return fig


def create_price_vs_score_plot(data):
    Q1 = data['Price'].quantile(0.25)
    Q3 = data['Price'].quantile(0.75)
    IQR = Q3 - Q1
    data = data.query('(@Q1 - 1.5 * @IQR) <= Price <= (@Q3 + 1.5 * @IQR)')

    fig, ax = plt.subplots()
    sns.scatterplot(x=data['Score'], y=data['Price'], ax=ax)
    ax.set_xlabel("Score")
    ax.set_ylabel("Price")
    ax.set_title("Price vs Score")
    return fig


def create_predicted_prices_plot(districts, predicted_prices, scaler, X_future):
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.barplot(x=districts, y=predicted_prices.flatten(), ax=ax)
    ax.set_title('Predicted Prices by District')
    ax.set_xlabel('District')
    ax.set_ylabel('Price')
    return fig


def create_mean_price_trend_plot(data, model, scaler, future_data):
    district_figures = []

    for district in data['District'].unique():
        fig, ax = plt.subplots(figsize=(10, 5))

        # Filter district data and sort by 'Start Date'
        district_data = data[data['District'] == district]
        district_data = district_data.sort_values(by='Start Date')

        # Plot historical data
        ax.plot(district_data['Start Date'], district_data['Price'], label=f'District {district}')

        # Filter and sort future predictions
        future_district_data = future_data[future_data['District'] == district]
        future_district_data = future_district_data.sort_values(by='YearMonth')

        # Get future district X values
        X_future = future_district_data[['District', 'Score', 'Review Count', 'Nights', 'Guests']]
        X_future_scaled = scaler.transform(X_future)

        # Predict future prices using the model
        predicted_future_prices = model.predict(X_future_scaled)

        # Plot future predictions
        ax.plot(future_district_data['YearMonth'], predicted_future_prices.flatten(),
                label=f'District {district} (Predicted)')

        ax.set_title('Price Trend by District')
        ax.set_xlabel('Date')
        ax.set_ylabel('Price')
        ax.legend()
        district_figures.append(fig)

    return district_figures


def create_future_scenarios(districts, data):
    future_dates = pd.date_range(start='2023-06-05', periods=365)
    future_data = pd.DataFrame({'YearMonth': future_dates})

    # Repeat the values for each district until the lengths match
    district_repeats = len(future_dates) // len(districts)
    district_remainder = len(future_dates) % len(districts)

    district_values = np.repeat(districts, district_repeats)[:len(future_dates)]
    district_values = np.append(district_values, districts[:district_remainder])

    future_data['District'] = district_values

    # Use sample values from data for future scenarios
    future_data['Score'] = np.random.choice(data['Score'], size=len(future_dates))
    future_data['Review Count'] = np.random.choice(data['Review Count'], size=len(future_dates))
    future_data['Nights'] = np.random.choice(data['Nights'], size=len(future_dates))
    future_data['Guests'] = np.random.choice(data['Guests'], size=len(future_dates))

    return future_data


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7000, debug=True)
