"""Tests that the database can be created, read, and written to."""

import database

database.create()
data = database.read()
print(data.schedule_to_str())
database.write(data)
print(data.schedule_to_str())
