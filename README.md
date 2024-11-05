# Doorbell
A Slack bot used by Armada Robotics to notify when people need to be let in along with some extra functionality.

## Setup
Assuming you already have Git and Python (>=3.12) installed.
```
git clone https://github.com/WispySparks/Doorbell.git
```
I would recommend creating a virtual environment.
```
python -m venv .venv
```
And activate it by running the appropriate script under `.venv/Scripts/`. <br>
Installing dependencies. 
```
pip install -r ./requirements.txt
```
Doorbell depends on some Slack tokens which should be stored in a `src/secret.py` file with their values. You can see their imports in `src/app.py`. These tokens can be found on [Slack Apps](https://api.slack.com/apps). Also the first time you run the bot it will have you sign into the Armada Robotics Google account so that it can store the relevant tokens for accessing the Google calendar.

### Running
To run Doorbell normally simply launch `src/app.py`.
```
python src/app.py
```
If you want to log to a file (if you're running Doorbell silently) then add the `-l` flag.
```
python src/app.py -l
```
Generally you'll want Doorbell to run automatically when your server/computer starts up. For Windows you can use the Task Scheduler or cron for Unix. The Task Scheduler gui is pretty self explanatory just make sure you're running the python from your virtual environment.

### Setting up Spicetify / Spotify integration
Doorbell's Spotify integration works by loading a custom extension using [Spicetify](https://spicetify.app/).
Follow the instructions [here](https://spicetify.app/docs/getting-started#installation) on how to install Spicetify.
You'll also need to download Node.js/npm to build the Spicetify extension. This can be installed from [here](https://nodejs.org/en/download/prebuilt-installer).
After installing those two navigate to the `spicetify-extension` directory and run the following commands.
```
npm run build
```
```
spicetify config extensions doorbell-integration.js 
```
```
spicetify apply
```
And you're done! Whenever Spotify is open it will automatically connect to Doorbell and start listening for song requests.
