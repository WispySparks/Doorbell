import sys

sys.path.append("src/")
import database

database.create()
data = database.read()
print(data.schedule_to_str())
database.write(data)
print(data.schedule_to_str())
