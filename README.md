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
Doorbell depends on some Slack tokens which should be stored in a `src/secret.py` file with their values. You can see their imports in `src/app.py`. These tokens can be found on [Slack Apps](https://api.slack.com/apps). You will also need to download the ouath client secret from [Google Developer Console](https://console.cloud.google.com/project), rename it to `credentials.json` and place it at the root of this repository. The first time you run the bot it will have you sign into the Armada Robotics Google account so that it can store the relevant tokens for accessing the Google calendar.

### Running
To run Doorbell normally simply launch `src/app.py`.
```
python src/app.py
```
If you want to log to a file (if you're running Doorbell silently) then add the `-l` flag.
```
python src/app.py -l
```
Generally you'll want Doorbell to run automatically when your server/computer starts up. For Windows you can use the Task Scheduler or cron for Unix. Here's a command for creating a Windows Task that starts Doorbell everytime the computer turns on.
```bat
schtasks /Create /TN "Doorbell" /TR "\"C:/path/to/.venv/Scripts/pythonw.exe\" \"C:/path/to/Doorbell/src/app.py\" -l" /SC ONSTART /RU yourusername /RP
```
That gets you most of the way there but you should access the task in the GUI and set the task -> properties -> actions -> "start in" to the root of Doorbell (C:/path/to/Doorbell).

### Setting up Spicetify / Spotify integration
Doorbell's Spotify integration works by loading a custom extension using [Spicetify](https://spicetify.app/).
Follow the instructions [here](https://spicetify.app/docs/getting-started#installation) on how to install Spicetify.
You'll also need to download Node.js/npm to build the Spicetify extension. This can be installed from [here](https://nodejs.org/en/download/prebuilt-installer).
After installing those two navigate to the `spicetify-extension` directory and run the following commands.
```
npm install
```
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
