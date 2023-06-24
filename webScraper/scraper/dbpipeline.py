from io import BytesIO
import mysql.connector
from datetime import date
from flask import send_file
from openpyxl import Workbook


class WebscrapeMysqlPipeline:

    def __init__(self):
        self.conn = mysql.connector.connect(
            host='db',
            port=3306,
            user='root',
            password='root',
        )

        self.cursor = self.conn.cursor()

        self.cursor.execute("CREATE DATABASE IF NOT EXISTS scraperdb")
        self.conn.commit()
        self.cursor.execute("USE scraperdb")  # Select the scraperdb to be used

        # connect to db
        self.conn = mysql.connector.connect(
            host='db',
            port=3306,
            user='root',
            password='root',
            database='scraperdb'
        )

        # create cursor
        self.cursor = self.conn.cursor()

        # if table does not exist on init create hotels
        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS scraperdb.hotels(
                id INT AUTO_INCREMENT PRIMARY KEY, 
                hotelname VARCHAR(255) NOT NULL,
                address VARCHAR(255) NOT NULL,
                configuration VARCHAR(255) NOT NULL,
                location VARCHAR(255) NOT NULL,
                distance VARCHAR(255) NOT NULL
            )""")

        # if table does not exist on init create prices
        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS scraperdb.prices(
                id INT AUTO_INCREMENT PRIMARY KEY, 
                hotelname VARCHAR(255) NOT NULL,
                price VARCHAR(20),
                scrapdate DATE, 
                startdate DATE,
                enddate DATE,
                guests INT,
                score VARCHAR(5),
                reviewCount VARCHAR(255)
            )""")

        self.conn.commit()

    def check_tables(self):
        # check if tables have been created
        print("\n\n --<>-- Show tables --<>-- ")
        self.cursor.execute(""" SHOW TABLES """)
        for a in self.cursor:
            print(a)

    def check_hotels_in_db(self, name):
        # check if hotel is already in db
        self.cursor.execute("""SELECT * FROM scraperdb.hotels WHERE hotelname = %s""", (name,))
        if self.cursor.fetchone() is None:
            return False
        else:
            return True

    def process_item(self, item):
        # if hotel does not exist add it to table hotels
        self.cursor.execute("""SELECT * FROM scraperdb.hotels WHERE hotelname = %s""", (item['name'],))

        status = 'duplicate'
        # if hotel does not exist add it to table hotels
        if self.cursor.fetchone() is None:
            # set status to new hotel
            status = 'new'
            self.cursor.execute("""
                    INSERT INTO scraperdb.hotels(hotelname, address, configuration, location, distance)
                    VALUES(%s, %s, %s, %s, %s)
                    """, (
                item['name'],
                item['address'],
                item['configuration'],
                item['location'],
                item['distance']
            ))

        # add price to table prices
        self.cursor.execute("""
                INSERT INTO scraperdb.prices(hotelname, price, scrapdate, startdate, enddate, guests, score, reviewCount)
                VALUES(%s, %s, CURDATE(), %s, %s, %s, %s, %s)
                """, (
            item['name'],
            item['price'],
            item['checkin'],
            item['checkout'],
            item['group_adults'],
            item['score'],
            item['reviewCount']
        ))

        # If there were no issues, commit the transaction
        self.conn.commit()

        return status

    def send_xlsx_as_download(self):
        filename = str(date.today()) + "_scraped_export.xlsx"
        print(filename)

        filepath = "C:/Users/vikto/Documents/FH Campus Wien/4. Semester/WPF Projekt/" + filename

        # get data from both tables of the db
        self.cursor.execute("""
                    SELECT hotels.hotelname, hotels.address, prices.price, prices.scrapdate, prices.startdate,
                        prices.enddate, prices.guests, prices.score, prices.reviewCount
                    FROM hotels
                    INNER JOIN prices ON hotels.hotelname = prices.hotelname
                    ORDER BY hotels.hotelname
                """)
        # fetch data from db to variable data
        data = self.cursor.fetchall()

        # create Excel file
        workbook = Workbook()
        # create sheet
        sheet = workbook.active
        # name sheet
        sheet.title = filename
        # adding column names to sheet
        sheet.append(
            ['Hotel Name', 'Address', 'Price', 'Scrap Date', 'Datum', 'Nights', 'Guests', 'Score', 'Review Count'])
        # adding data to sheet
        for row in data:
            sheet.append(row)

        # Save the XLSX file to a binary stream
        output = BytesIO()
        workbook.save(output)

        # Send the binary stream as a response
        output.seek(0)
        return send_file(output, as_attachment=True, attachment_filename=filename + '.xlsx',
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    def export_db(self, path, filename):
        # export db to excel

        print(filename)

        filepath = path + "/" + filename

        # get data from both tables of the db
        self.cursor.execute("""
            SELECT hotels.hotelname, hotels.address, prices.price, prices.scrapdate, prices.startdate,
                prices.enddate, prices.guests, prices.score, prices.reviewCount
            FROM hotels
            INNER JOIN prices ON hotels.hotelname = prices.hotelname
            ORDER BY hotels.hotelname
        """)
        # fetch data from db to variable data
        data = self.cursor.fetchall()

        # create Excel file
        workbook = Workbook()
        # create sheet
        sheet = workbook.active
        # name sheet
        sheet.title = filename
        # adding column names to sheet
        sheet.append(
            ['Hotel Name', 'Address', 'Price', 'Scrap Date', 'Datum', 'Nights', 'Guests', 'Score', 'Review Count'])
        # adding data to sheet
        for row in data:
            sheet.append(row)

        # save Excel file to path
        workbook.save(filename=filepath)

    def delete_tables(self):
        # delete tables hotels and prices
        self.cursor.execute(""" DROP TABLE scraperdb.hotels """)
        self.cursor.execute(""" DROP TABLE scraperdb.prices """)
        self.conn.commit()

    def close_pipeline(self):
        # close connection
        self.conn.close()
