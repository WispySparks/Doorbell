function createSocket() {
  const websocket = new WebSocket("ws://localhost:8765/");
  websocket.onopen = () => console.log("Doorbell Integration: Connected to Doorbell.");
  websocket.onmessage = (event) => {
    const uri = Spicetify.URI.from(event.data);
    if (uri) {
      Spicetify.addToQueue([{ uri: uri.toURI() }]);
    }
  }
  websocket.onclose = () => {
    console.log("Doorbell Integration: Connection failed/closed with Doorbell.");
    setTimeout(createSocket, 10000)
  }
}

async function main() {
  console.log("Doorbell Integration: Started.")
  createSocket()
}

export default main;
