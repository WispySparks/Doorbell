"""Tests that the database can be created, read, and written to."""

from doorbell_test import MockDoorbell

import database

d = MockDoorbell()
database.create()
data = database.read()
print(data.schedule_to_str())
print(data.all_subscriptions_to_str(d))
database.write(data)
print(data.schedule_to_str())
print(data.all_subscriptions_to_str(d))
d.close()
