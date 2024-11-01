async function main() {
  console.log("Doorbell Integration: Starting.")
  const websocket = new WebSocket("ws://localhost:8765/");
  websocket.onopen = () => console.log("Doorbell Integration: Connected to Doorbell.");
  websocket.onmessage = (event) => {
    const uri = Spicetify.URI.fromString(event.data);
    if (uri) {
      Spicetify.Player.playUri(uri.toURI());
    }
  }
}

export default main;
