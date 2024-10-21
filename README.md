<h1>Usage</h1>
python3 -m venv venv
source venv/bin/activate
pip install requirements.txt

Our code utilizes the pyaudio library. To use it, you have to install the portaudio library.

for windows:
sudo apt-get install portaudio19-dev
for mac:
brew install portaudio


<h1>For Developers</h1>
pip freeze > requirements.txt
fastapi dev server.py
