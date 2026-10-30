from flask import Flask, flash, render_template, request, redirect, url_for, session
import mysql.connector

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="vehicle_service_db"
    )



app = Flask(__name__)
app.secret_key = "vehiclecare_secret_key"

db =mysql.connector.connect(
    host="localhost",
    user="root",
    password="root",
    database="vehicle_service_db"
)

print("MySQL connected successfully!")


@app.route("/")
def home():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        cursor = db.cursor()

        query = """
        INSERT INTO users (name, email, password)
        VALUES (%s, %s, %s)
        """

        cursor.execute(query, (name, email, password))

        db.commit()

        cursor.close()

        return "Registration successful!"

    return render_template("register.html")
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        cursor = db.cursor()

        query = """
        SELECT *
        FROM users
        WHERE email = %s
        AND password = %s
        """

        cursor.execute(query, (email, password))

        user = cursor.fetchone()

        cursor.close()

        if user:

            session["user_id"] = user[0]
            session["user_name"] = user[1]
            session["role"] = user[4]

            if user[4] == "admin":
                return redirect(url_for("admin_dashboard"))

            return redirect(url_for("dashboard"))

        return "Invalid email or password!"

    return render_template("login.html")
#logout
@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))
#dashboard
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    cursor = db.cursor()

    try:
        # Get customer's vehicles
        cursor.execute(
            "SELECT * FROM vehicles WHERE user_id = %s",
            (user_id,)
        )
        vehicles = cursor.fetchall()

        # Get service requests and assigned mechanics
        service_query = """
            SELECT
                services.id,
                vehicles.vehicle_number,
                services.service_type,
                services.description,
                services.service_date,
                services.status,
                mechanics.name,
                mechanics.specialization
            FROM services
            JOIN vehicles ON services.vehicle_id = vehicles.id
            LEFT JOIN service_assignments
                ON service_assignments.id = (
                    SELECT MAX(sa2.id)
                    FROM service_assignments sa2
                    WHERE sa2.service_id = services.id
                )
            LEFT JOIN mechanics
                ON mechanics.id = service_assignments.mechanic_id
            WHERE vehicles.user_id = %s
            ORDER BY services.id DESC
        """
        cursor.execute(service_query, (user_id,))
        services = cursor.fetchall()

        # Get customer's invoices
        invoice_query = """
            SELECT
                invoices.id,
                invoices.service_id,
                invoices.labour_cost,
                invoices.parts_cost,
                invoices.total_amount,
                invoices.invoice_date,
                invoices.payment_status,
                vehicles.vehicle_number,
                services.service_type
            FROM invoices
            JOIN services ON invoices.service_id = services.id
            JOIN vehicles ON services.vehicle_id = vehicles.id
            WHERE vehicles.user_id = %s
            ORDER BY invoices.id DESC
        """
        cursor.execute(invoice_query, (user_id,))
        invoices = cursor.fetchall()

    finally:
        cursor.close()

    return render_template(
        "dashboard.html",
        vehicles=vehicles,
        services=services,
        invoices=invoices
    )


#add vehicle
@app.route("/add_vehicle", methods=["GET", "POST"])
def add_vehicle():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        vehicle_number = request.form["vehicle_number"]
        brand = request.form["brand"]
        model = request.form["model"]
        year = request.form["year"]
        fuel_type = request.form["fuel_type"]

        cursor = db.cursor()

        query = """
        INSERT INTO vehicles
        (user_id, vehicle_number, brand, model, year, fuel_type)
        VALUES (%s, %s, %s, %s, %s, %s)
        """

        user_id = session["user_id"]

        cursor.execute(
            query,
            (user_id, vehicle_number, brand, model, year, fuel_type)
        )

        db.commit()
        cursor.close()

        return redirect(url_for("dashboard"))

    return render_template("add_vehicle.html")
#book service
@app.route("/book_service", methods=["GET", "POST"])
def book_service():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    cursor = db.cursor()

    # Get vehicles belonging to logged-in user
    cursor.execute(
        "SELECT * FROM vehicles WHERE user_id = %s",
        (user_id,)
    )

    vehicles = cursor.fetchall()

    if request.method == "POST":

        vehicle_id = request.form["vehicle_id"]
        service_type = request.form["service_type"]
        description = request.form["description"]
        service_date = request.form["service_date"]

        query = """
        INSERT INTO services
        (vehicle_id, service_type, description, service_date)
        VALUES (%s, %s, %s, %s)
        """

        cursor.execute(
            query,
            (vehicle_id, service_type, description, service_date)
        )

        db.commit()

        cursor.close()

        return redirect(url_for("dashboard"))

    cursor.close()

    return render_template(
        "book_service.html",
        vehicles=vehicles
    )
@app.route("/add_mechanic", methods=["GET", "POST"])
def add_mechanic():

    if "user_id" not in session:
        return redirect(url_for("login"))
    if session.get("role") != "admin":
        return "Access denied! Admins only.", 403

    if request.method == "POST":

        name = request.form["name"]
        specialization = request.form["specialization"]
        phone = request.form["phone"]

        cursor = db.cursor()

        query = """
        INSERT INTO mechanics
        (name, specialization, phone)
        VALUES (%s, %s, %s)
        """

        cursor.execute(
            query,
            (name, specialization, phone)
        )

        db.commit()

        cursor.close()

        return "Mechanic added successfully!"

    return render_template("add_mechanic.html")
@app.route("/edit_mechanic/<int:mechanic_id>", methods=["GET", "POST"])
def edit_mechanic(mechanic_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        return "Access denied! Admins only.", 403

    cursor = db.cursor()

    if request.method == "POST":

        name = request.form["name"]
        specialization = request.form["specialization"]
        phone = request.form["phone"]

        cursor.execute("""
            UPDATE mechanics
            SET name = %s,
                specialization = %s,
                phone = %s
            WHERE id = %s
        """, (name, specialization, phone, mechanic_id))

        db.commit()
        cursor.close()

        return redirect(url_for("admin_mechanics"))

    cursor.execute("""
        SELECT id, name, specialization, phone
        FROM mechanics
        WHERE id = %s
    """, (mechanic_id,))

    mechanic = cursor.fetchone()

    cursor.close()

    if mechanic is None:
        return "Mechanic not found.", 404

    return render_template(
        "edit_mechanic.html",
        mechanic=mechanic
    )
@app.route("/delete_mechanic/<int:mechanic_id>", methods=["POST"])
def delete_mechanic(mechanic_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        return "Access denied! Admins only.", 403

    cursor = db.cursor()

    cursor.execute("""
        DELETE FROM mechanics
        WHERE id = %s
    """, (mechanic_id,))

    db.commit()
    cursor.close()

    return redirect(url_for("admin_mechanics"))
@app.route("/mechanics")
def mechanics():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        return "Access denied! Admins only.", 403

    return redirect(url_for("admin_mechanics"))
@app.route("/assign_mechanic", methods=["GET", "POST"])
def assign_mechanic():

    if "user_id" not in session:
        return redirect(url_for("login"))
    if session.get("role") != "admin":
        return "Access denied! Admins only.", 403

    cursor = db.cursor()

    # Get all service requests
    service_query = """
    SELECT services.id,
           vehicles.vehicle_number,
           services.service_type
    FROM services
    JOIN vehicles
    ON services.vehicle_id = vehicles.id
    ORDER BY services.id DESC
    """

    cursor.execute(service_query)
    services = cursor.fetchall()

    # Get all mechanics
    cursor.execute("""
        SELECT id, name, specialization
        FROM mechanics
        ORDER BY id DESC
    """)

    mechanics = cursor.fetchall()

    if request.method == "POST":

        service_id = request.form["service_id"]
        mechanic_id = request.form["mechanic_id"]
        assigned_date = request.form["assigned_date"]

        query = """
        INSERT INTO service_assignments
        (service_id, mechanic_id, assigned_date)
        VALUES (%s, %s, %s)
        """

        cursor.execute(
            query,
            (service_id, mechanic_id, assigned_date)
        )

        db.commit()

        cursor.close()

        return redirect(url_for("admin_services")) 

    cursor.close()

    return render_template(
        "assign_mechanic.html",
        services=services,
        mechanics=mechanics
    )
@app.route("/update_status", methods=["GET", "POST"])
def update_status():

    if "user_id" not in session:
        return redirect(url_for("login"))
    if session.get("role") != "admin":
        return "Access denied! Admins only.", 403

    cursor = db.cursor()

    # Get all service requests
    query = """
    SELECT services.id,
           vehicles.vehicle_number,
           services.service_type,
           services.status
    FROM services
    JOIN vehicles
    ON services.vehicle_id = vehicles.id
    ORDER BY services.id DESC
    """

    cursor.execute(query)

    services = cursor.fetchall()

    if request.method == "POST":

        service_id = request.form["service_id"]
        status = request.form["status"]

        update_query = """
        UPDATE services
        SET status = %s
        WHERE id = %s
        """

        cursor.execute(
            update_query,
            (status, service_id)
        )

        db.commit()

        cursor.close()

        return redirect(url_for("dashboard"))

    cursor.close()

    return render_template(
        "update_status.html",
        services=services
    )
@app.route("/admin")
def admin_dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        return "Access denied! Admins only.", 403

    cursor = db.cursor()

    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'customer'")
    total_customers = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM vehicles")
    total_vehicles = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM services")
    total_services = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM mechanics")
    total_mechanics = cursor.fetchone()[0]
    cursor.execute("""
    SELECT COALESCE(SUM(total_amount), 0)
    FROM invoices
    WHERE payment_status = 'Paid'
    """)
    total_revenue = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*)
    FROM invoices
    WHERE payment_status = 'Paid'
    """)
    paid_count = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*)
    FROM invoices
    WHERE payment_status = 'Pending'
    """)
    pending_count = cursor.fetchone()[0]

    cursor.close()

    return render_template(
        "admin_dashboard.html",
        total_customers=total_customers,
        total_vehicles=total_vehicles,
        total_services=total_services,
        total_mechanics=total_mechanics,
        total_revenue=total_revenue,
        paid_count=paid_count,
        pending_count=pending_count
    
        
)
@app.route("/admin_services")
def admin_services():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        return "Access denied! Admins only.", 403

    cursor = db.cursor()


    cursor.execute("""
        SELECT
            s.id,
            s.vehicle_id,
            s.service_type,
            s.description,
            s.service_date,
            s.status,
            m.name,
            m.specialization

        FROM services s

        LEFT JOIN service_assignments sa
            ON sa.id = (
                SELECT MAX(sa2.id)
                FROM service_assignments sa2
                WHERE sa2.service_id = s.id
            )

        LEFT JOIN mechanics m
            ON m.id = sa.mechanic_id

        ORDER BY s.service_date DESC
    """)

    services = cursor.fetchall()

    cursor.close()

    return render_template(
        "admin_services.html",
        services=services
    )
@app.route("/admin_mechanics")
def admin_mechanics():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        return "Access denied! Admins only.", 403

    cursor = db.cursor()

    cursor.execute("""
        SELECT id, name, specialization, phone
        FROM mechanics
        ORDER BY id DESC
    """)

    mechanics = cursor.fetchall()

    cursor.close()

    return render_template(
        "admin_mechanics.html",
        mechanics=mechanics
    )

@app.route("/update_service_status", methods=["POST"])
def update_service_status():

    # Check login
    if "user_id" not in session:
        return redirect(url_for("login"))

    # Only admin can update service status
    if session.get("role") != "admin":
        return "Access denied! Admins only.", 403

    service_id = request.form.get("service_id")
    new_status = request.form.get("status")

    # Allowed statuses
    allowed_statuses = [
        "Requested",
        "In Progress",
        "Completed",
        "Cancelled"
    ]

    if new_status not in allowed_statuses:
        return "Invalid service status.", 400

    cursor = db.cursor()

    cursor.execute(
        """
        UPDATE services
        SET status = %s
        WHERE id = %s
        """,
        (new_status, service_id)
    )

    db.commit()
    cursor.close()

    return redirect(url_for("admin_services"))
@app.route("/admin_invoices")
def admin_invoices():

    if "user_id" not in session or session.get("role") != "admin":
        return redirect("/login")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            invoices.id,
            invoices.service_id,
            invoices.labour_cost,
            invoices.parts_cost,
            invoices.total_amount,
            invoices.invoice_date,
            invoices.payment_status,
            vehicles.vehicle_number,
            services.service_type
        FROM invoices
        JOIN services
            ON invoices.service_id = services.id
        JOIN vehicles
            ON services.vehicle_id = vehicles.id
        ORDER BY invoices.id DESC
    """)

    invoices = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "admin_invoices.html",
        invoices=invoices
    )
@app.route("/update_invoice_status/<int:invoice_id>", methods=["POST"])
def update_invoice_status(invoice_id):

    if "user_id" not in session or session.get("role") != "admin":
        return redirect("/login")

    payment_status = request.form.get("payment_status")

    if payment_status not in ["Pending", "Paid"]:
        return redirect("/admin_invoices")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE invoices
        SET payment_status = %s
        WHERE id = %s
    """, (payment_status, invoice_id))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/admin_invoices")

@app.route("/view_invoice/<int:invoice_id>")
def view_invoice(invoice_id):

    if "user_id" not in session or session.get("role") != "admin":
        return redirect("/login")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            invoices.id AS invoice_id,
            invoices.service_id,
            invoices.labour_cost,
            invoices.parts_cost,
            invoices.total_amount,
            invoices.invoice_date,
            services.service_type,
            vehicles.vehicle_number
        FROM invoices
        JOIN services
            ON invoices.service_id = services.id
        JOIN vehicles
            ON services.vehicle_id = vehicles.id
        WHERE invoices.id = %s
    """, (invoice_id,))

    invoice = cursor.fetchone()

    cursor.close()
    conn.close()

    if not invoice:
        return "Invoice not found", 404

    return render_template(
        "view_invoice.html",
        invoice=invoice
    )
@app.route("/create_invoice", methods=["GET", "POST"])
def create_invoice():
    if "user_id" not in session or session.get("role") != "admin":
        return redirect("/login")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":
        service_id = request.form["service_id"]
        labour_cost = float(request.form["labour_cost"])
        parts_cost = float(request.form["parts_cost"])

        total_amount = labour_cost + parts_cost

        cursor.execute("""
            INSERT INTO invoices
            (service_id, labour_cost, parts_cost,
             total_amount, invoice_date)
            VALUES (%s, %s, %s, %s, CURDATE())
        """, (service_id, labour_cost, parts_cost, total_amount))

        conn.commit()
        cursor.close()
        conn.close()

        return redirect("/admin_invoices")

    cursor.execute("""
    SELECT
        services.id AS id,
        vehicles.vehicle_number,
        services.service_type
    FROM services
    JOIN vehicles
        ON services.vehicle_id = vehicles.id
    """)

    services = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("create_invoice.html", services=services)
@app.route("/my_invoices")
def my_invoices():

    # Check customer login
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            invoices.id AS invoice_id,
            invoices.labour_cost,
            invoices.parts_cost,
            invoices.total_amount,
            invoices.invoice_date,
            invoices.payment_status,
            services.service_type,
            vehicles.vehicle_number
        FROM invoices
        JOIN services
            ON invoices.service_id = services.id
        JOIN vehicles
            ON services.vehicle_id = vehicles.id
        WHERE vehicles.user_id = %s
        ORDER BY invoices.id DESC
    """, (session["user_id"],))

    invoices = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "my_invoices.html",
        invoices=invoices
    )
@app.route("/feedback", methods=["GET", "POST"])
def feedback():
 if "user_id" not in session:
  return redirect("/login")


 if request.method == "POST":
    rating = request.form.get("rating", type=int)
    comments = request.form.get("comments", "").strip()

    if rating not in (1, 2, 3, 4, 5) or not comments:
       flash("Please select a rating and enter your comments.", "error")
    return redirect("/feedback")

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO feedback (user_id, rating, comments)
            VALUES (%s, %s, %s)
            """,
            (session["user_id"], rating, comments)
        )
        conn.commit()
        flash("Thank you! Your feedback was submitted successfully.", "success")

    except Exception:
        conn.rollback()
        flash("Unable to submit feedback. Please try again.", "error")

    finally:
        cursor.close()
        conn.close()

    return redirect("/feedback")

 return render_template("feedback.html")


if __name__ == "__main__":
    app.run(debug=True)