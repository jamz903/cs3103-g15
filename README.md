# Push-To-Talk WebSocket Application
The aim of this push-to-talk (PTT) application is to enable a one-way, real time audio streaming from the student’s device to the lecturer’s PC utilising WebSockets from FastAPI. This serves as a proof of concept that it is possible to transmit raw audio data (that may require splitting up into chunks) via websockets and outputting it in a suitable form to be played on a loudspeaker on the lecturer side. At any given time, only one student can send his/her voice to the lecturer – the concurrency is managed by our application. 

![alt text](CS3103Assignment4.png)


# Usage

## To run the code:

*Note: You will need to install Python 3.10. If not, you will face errors running our code.*

`python3 -m venv venv`

`source venv/bin/activate`

`pip install -r requirements.txt`

`fastapi dev server.py`

If you are unable to run the fastapi command, it is most likely that you have an existing venv. Delete the venv folder and reinstall the packages.


Our code utilizes the pyaudio library. To use it, you have to install the portaudio library.

for windows:
`sudo apt-get install portaudio19-dev`

for mac:
`brew install portaudio`

### For Developers
`pip freeze > requirements.txt` everytime there is updates to the requirements

`fastapi dev server.py`
