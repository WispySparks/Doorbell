async function main() {
  // Now I just have to grab this from python
  let uri = Spicetify.URI.from("https://open.spotify.com/track/54bm2e3tk8cliUz3VSdCPZ?si=aa8385c7cd4a4090");
  if (uri) {
    await Spicetify.Player.playUri(uri.toURI());
  }
}

export default main;
