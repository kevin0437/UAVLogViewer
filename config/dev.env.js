'use strict'
const { merge } = require('webpack-merge')
const prodEnv = require('./prod.env')

module.exports = merge(prodEnv, {
  NODE_ENV: '"development"',
  CESIUM_ION_ACCESS_TOKEN: '"YOUR TOKEN HERE!"'
})
