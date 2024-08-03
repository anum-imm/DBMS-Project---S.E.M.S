import psycopg2
from datetime import datetime, date, time


from flask import Flask, render_template, request, flash, redirect, url_for

app = Flask(__name__)
app.secret_key = "your_secret_key"

def get_conn():
    try:
        conn = psycopg2.connect(
            dbname="dbmsproject",
            user="postgres",
            password="tech",
            host="localhost"

        )
        return conn
    except Exception as e:
        flash(f"Error connecting to the database: {e}", "error")
        return None

def fetch_events():
    conn = get_conn()
    if not conn:
        return []

    cur = conn.cursor()
    cur.execute("""
        SELECT Events.EventId, Events.EventName, Events.SeatNumber, Events.TicketPrice, 
               Artist.ArtistName, Club.VenueName, Events.EventStatus, Events.EventDate 
        FROM Events 
        JOIN Artist ON Events.ArtistId = Artist.ArtistId 
        JOIN Club ON Events.VenueId = Club.VenueId
    """)
    events = cur.fetchall()
    cur.close()
    conn.close()
    return events

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/events')
def events():
    events = fetch_events()
    return render_template('events.html', events=events)

@app.route('/booking', methods=['GET', 'POST'])
def booking():
    print(request.method)  # Print the method being used
    if request.method == 'POST':
        # Process the booking
        event_id = request.form['event']
        tickets = int(request.form['tickets'])
        
        flash('Booking successful!', 'success')
        return redirect(url_for('confirmation', event_id=event_id, tickets=tickets))
    else:
        events = fetch_events()
        print(events)  # Print the events fetched
        return render_template('booking.html', events=events)

@app.route('/additional_booking', methods=['POST'])

def additional_booking():
    # Retrieve event ID and tickets from the URL parameters
   # event_id = request.args.get('event')
    #tickets = request.args.get('tickets')
    event_id = request.form.get('event')
    tickets = request.form.get('tickets')
    
    # Render the additional_booking template with event ID and number of tickets
    return render_template('additional_booking.html', event_id=event_id, tickets=tickets)
@app.route('/booking_confirmation', methods=['POST'])
def booking_confirmation():
    # Retrieve data from the form submitted by the user
    event_id = request.form.get('event_id')
    tickets = request.form.get('tickets')
    name = request.form.get('name')
    account_name = request.form.get('username')
    account_id = request.form.get('account_id')
    email = request.form.get('email')
    payment_method = request.form.get('payment_method') 
    
    # Retrieve event details from the database based on the event ID
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT EventName, TicketPrice
        FROM Events 
        WHERE EventId = %s
    """, (event_id,))
    event_details = cur.fetchone()
    
    if event_details:
        event_name = event_details[0]
        ticket_price = event_details[1]
        
        # Calculate total price
        total_price = float(ticket_price) * int(tickets)
        
        # Retrieve account details from the database based on the account ID
        cur.execute("""
            SELECT AccountName, Email
            FROM Account 
            WHERE AccountId = %s
        """, (account_id,))
        account_details = cur.fetchone()
        
        if account_details:
            account_name = account_details[0]
            email = account_details[1]
        
        # Insert user data into the database
        cur.execute("""
            INSERT INTO Booking (TicketNumber, EventId, AmountToBePaid, BookingStatus, BookingDate)
            VALUES (%s, %s, %s, %s, CURRENT_DATE)
            RETURNING BookingId  -- Retrieve the BookingId after insertion
        """, (tickets, event_id, total_price, 'active'))
        
        booking_id = cur.fetchone()[0]  # Fetch the BookingId
        
        cur.execute("""
         INSERT INTO Payment (BookingId, AccountId, PaymentAmount, PaymentDate, PaymentMethod)
           VALUES (%s, %s, %s, %s, %s)
        """, (booking_id, account_id, total_price, date.today(), payment_method))

        

        # Commit changes to the database
        conn.commit()

        
        # Close cursor and connection
        cur.close()
        conn.close()
        
        
        # Pass retrieved data to the confirmation template along with the booking_id
        return render_template('booking_confirmation.html', 
                               booking_id=booking_id,
                               event_id=event_id, 
                               event_name=event_name,
                               tickets=tickets, 
                               account_name=account_name, 
                               account_id=account_id, 
                               email=email,
                               total_price=total_price)

@app.route('/cancel_booking', methods=['POST'])
def cancel_booking():
    if request.method == 'POST':
        booking_id = request.form['booking_id']

        # Fetch booking details including the event name
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT Booking.*, Events.EventName 
            FROM Booking 
            INNER JOIN Events ON Booking.EventId = Events.EventId 
            WHERE Booking.BookingId = %s
            """, (booking_id,))
        booking = cur.fetchone()

        if booking:
            event_name = booking[-1]  # Get the last element which is the event name
            
            try:
                # Update event seat availability
                cur.execute("UPDATE Events SET SeatNumber = SeatNumber + %s WHERE EventId = %s", (booking[3], booking[2]))
              
                # Delete the booking from the database
                cur.execute("DELETE FROM Booking WHERE BookingId = %s", (booking_id,))
                
                conn.commit()
                cur.close()
                return render_template('cancel_confirmation.html', event_name=event_name)
            except psycopg2.Error as e:
                conn.rollback()
                return f"Error occurred: {e}"
        else:
            # Handle invalid booking ID
            return "Invalid Booking ID"

    return "Method not allowed"

 
if __name__ == '__main__':
    app.run(debug=True)

