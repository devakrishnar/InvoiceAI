import sqlite3


def create_database():

    connection = sqlite3.connect("invoices.db")

    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoices(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            invoice_number TEXT,
            vendor TEXT,
            date TEXT,
            total_amount TEXT,
            file_path TEXT,
            status TEXT DEFAULT 'Pending'
        )
    """)

    # Attempt to alter table if status column does not exist
    try:
        cursor.execute("ALTER TABLE invoices ADD COLUMN status TEXT DEFAULT 'Pending'")
    except sqlite3.OperationalError:
        pass  # Column already exists

    connection.commit()

    connection.close()



def save_invoice(
        filename,
        invoice_number,
        vendor,
        date,
        total_amount,
        file_path,
        status="Pending"
):

    connection = sqlite3.connect("invoices.db")

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO invoices(
            filename,
            invoice_number,
            vendor,
            date,
            total_amount,
            file_path,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            filename,
            invoice_number,
            vendor,
            date,
            total_amount,
            file_path,
            status
        )
    )

    new_id = cursor.lastrowid

    connection.commit()

    connection.close()

    return new_id



def update_invoice_status(invoice_id, status):

    connection = sqlite3.connect("invoices.db")

    cursor = connection.cursor()

    cursor.execute(
        "UPDATE invoices SET status = ? WHERE id = ?",
        (status, invoice_id)
    )

    connection.commit()

    connection.close()



def update_invoice_metadata(invoice_id, invoice_number, vendor, date, total_amount, status):

    connection = sqlite3.connect("invoices.db")

    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE invoices
        SET invoice_number = ?,
            vendor = ?,
            date = ?,
            total_amount = ?,
            status = ?
        WHERE id = ?
        """,
        (invoice_number, vendor, date, total_amount, status, invoice_id)
    )

    connection.commit()

    connection.close()



def check_invoice_exists(filename):

    connection = sqlite3.connect("invoices.db")

    cursor = connection.cursor()

    cursor.execute("SELECT id FROM invoices WHERE filename = ?", (filename,))

    row = cursor.fetchone()

    connection.close()

    return row is not None



def get_all_invoices():

    connection = sqlite3.connect("invoices.db")

    cursor = connection.cursor()

    cursor.execute("SELECT * FROM invoices ORDER BY id DESC")

    rows = cursor.fetchall()

    connection.close()

    return rows