const path = require('path');

module.exports = {
    entry: './index.js',
    output: {
	filename: 'bundle.js',
	path: __dirname,
    },
    mode: 'production',
};
