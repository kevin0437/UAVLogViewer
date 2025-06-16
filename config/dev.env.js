'use strict'
const { merge } = require('webpack-merge')
const prodEnv = require('./prod.env')

module.exports = merge(prodEnv, {
  NODE_ENV: '"development"',
  CESIUM_ION_ACCESS_TOKEN: '"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiIzOGUwOGM2OS0xNDBkLTRmYzMtODc1NC1iODE0MDZjYmNiOTEiLCJpZCI6MzA0NjAwLCJpYXQiOjE3NDc3ODk3MDR9.LlxloU-xFw4YIAq0fuJv2xe5y9-uX76JTr8OeO0w-7o"'
})
