#!/usr/bin/env python3
"""
Script to create a SQLite database for managing car-related data.
Creates the database file 'cars.db' if it doesn't exist.
Creates tables: vehicle, driver, race, and circuit if they don't exist.
Populates the tables with sample data if they are empty.
"""

import sqlite3
import os

# Database file path
DB_FILE = "cars.db"

def create_database():
    """Create the SQLite database if it doesn't exist."""
    if not os.path.exists(DB_FILE):
        print(f"Creating database file: {DB_FILE}")
        conn = sqlite3.connect(DB_FILE)
        conn.close()
        print("Database created successfully.")
    else:
        print(f"Database file {DB_FILE} already exists.")

def create_tables():
    """Create tables if they don't exist."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Create vehicle table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vehicle (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            make TEXT NOT NULL,
            model TEXT NOT NULL,
            year INTEGER,
            color TEXT,
            license_plate TEXT UNIQUE
        )
    """)

    # Create driver table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS driver (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            license_number TEXT UNIQUE,
            age INTEGER,
            nationality TEXT
        )
    """)

    # Create circuit table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS circuit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            location TEXT NOT NULL,
            length_km REAL,
            laps INTEGER
        )
    """)

    # Create race table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS race (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            date TEXT,
            circuit_id INTEGER,
            FOREIGN KEY (circuit_id) REFERENCES circuit(id)
        )
    """)

    conn.commit()
    print("Tables created successfully.")
    conn.close()

def populate_tables():
    """Populate tables with sample data if they are empty."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Check if vehicle table is empty
    cursor.execute("SELECT COUNT(*) FROM vehicle")
    if cursor.fetchone()[0] == 0:
        print("Populating vehicle table with sample data...")
        vehicles = [
            ("Toyota", "Corolla", 2020, "Blue", "ABC123"),
            ("Honda", "Civic", 2019, "Red", "XYZ789"),
            ("Ford", "Mustang", 2021, "Black", "DEF456"),
        ]
        cursor.executemany(
            "INSERT INTO vehicle (make, model, year, color, license_plate) VALUES (?, ?, ?, ?, ?)",
            vehicles
        )

    # Check if driver table is empty
    cursor.execute("SELECT COUNT(*) FROM driver")
    if cursor.fetchone()[0] == 0:
        print("Populating driver table with sample data...")
        drivers = [
            ("John Doe", "D12345", 30, "American"),
            ("Jane Smith", "D67890", 28, "British"),
            ("Mike Johnson", "D54321", 35, "Canadian"),
        ]
        cursor.executemany(
            "INSERT INTO driver (name, license_number, age, nationality) VALUES (?, ?, ?, ?)",
            drivers
        )

    # Check if circuit table is empty
    cursor.execute("SELECT COUNT(*) FROM circuit")
    if cursor.fetchone()[0] == 0:
        print("Populating circuit table with sample data...")
        circuits = [
            ("Monza Circuit", "Monza, Italy", 5.793, 53),
            ("Silverstone Circuit", "Silverstone, UK", 5.898, 52),
            ("Suzuka Circuit", "Suzuka, Japan", 5.807, 53),
        ]
        cursor.executemany(
            "INSERT INTO circuit (name, location, length_km, laps) VALUES (?, ?, ?, ?)",
            circuits
        )

    # Check if race table is empty
    cursor.execute("SELECT COUNT(*) FROM race")
    if cursor.fetchone()[0] == 0:
        print("Populating race table with sample data...")
        races = [
            ("Italian Grand Prix", "2023-09-10", 1),
            ("British Grand Prix", "2023-07-09", 2),
            ("Japanese Grand Prix", "2023-09-24", 3),
        ]
        cursor.executemany(
            "INSERT INTO race (name, date, circuit_id) VALUES (?, ?, ?)",
            races
        )

    conn.commit()
    print("Tables populated successfully.")
    conn.close()

def main():
    """Main function to create database, tables, and populate them."""
    print("Starting database setup...")
    create_database()
    create_tables()
    populate_tables()
    print("Database setup completed successfully.")

if __name__ == "__main__":
    main()