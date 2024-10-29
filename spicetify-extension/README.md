# Spicetify Creator

Spicetify Creator is a tool to compile modern Typescript/Javascript code to Spicetify extensions and custom apps.

## Features
- Typescript and React syntax
- Import node packages
- CSS/SCSS with PostCSS support
- Extremely fast compile time with esbuild.
- Plugins

## Docs
Check out [Spicetify's docs](https://spicetify.app/docs/development/spicetify-creator/the-basics)!

## Made with Spicetify Creator
- https://github.com/spicetify/spicetify-creator

## Building and applying
`npm run build` <br>
`spicetify config extensions doorbell-integration.js`<br>
`spicetify apply`
### One liner
```sh
npm run build && spicetify config extensions doorbell-integration.js && spicetify apply
```