var request = require('request');
var cheerio = require('cheerio');
var urll = require('url');
var http = require('http');
var asyncLoop = require('node-async-loop');
var fs = require('fs')
var outFile = "top500.txt"
					
function extract_content_size(url, complete) {
	request(url, function(error, response, html) {
		console.log(url);
		if (typeof html === 'undefined') {
			return complete([]);
		}

		// Find links
		var links = []
	    if(!error){
	        var $ = cheerio.load(html);
	        $('*').each(function() { 
			    var backImg;

			    // Images
			    if ($(this).is('img')) {
			        links.push($(this).attr('src'))
			    } else {
			        backImg = $(this).css('background-image');
			        if (typeof backImg !== 'undefined' && backImg != 'none') {
			        	links.push(backImg.substring(4, backImg.length-1))
			        }
			    }

			    // Stylesheets
			    if ($(this).is('link')) {
			    	links.push($(this).attr('href'))
			    }

			    // Scripts
			    if ($(this).is('script')) {
			    	var src = $(this).attr('src');
			    	if (typeof src !== 'undefined') links.push(src);
			    }
			});
	    }

	    // Timeout 
	    var done = 0;
	    var len = [html.length];
	    function idone() {
    		done++;
			if (done == links.length) {
				return complete(len);
			}
	    }

	    // Parse
	    for (var i = 0; i < links.length; i++) {
	    	if (typeof links[i] === 'undefined') {
	    		idone(); continue;
	    	}
	    	var link = urll.resolve(url, links[i]);
	    	try {
		    	var parse = urll.parse(link)
		    } catch (err) {
		    	console.log("parse error", err);
		    }
	    	var options = {method: 'HEAD', host: parse.host, port: parse.port, path: parse.path, agent: false};
			var req = http.request(options, 
				function(res) {
					var str = ''
					res.on('data', function (chunk) {
						str += chunk;
					});

					res.on('end', function () {
						// get content length
						length = res.headers["content-length"]
						if (typeof length !== 'undefined') {
							len.push(parseInt(length));
						}

						// Check for completion
						return idone();
					});
			  	}
			).on('socket', function (socket) {
			    socket.setTimeout(1 * 60000);  // 5 minutes
			    socket.on('timeout', function() {
			    	console.log("timeout");
			    	req.abort();
			    	return idone();
			    });
			}).on('error', function (exc) {
			    console.log("ignoring exception: " + exc);
			    return idone();
			});
			req.end();
	    }
	})

}

// Clear output
fs.writeFile(outFile, '', function(){console.log('clear')})

// Extract top 500 website size
var request = require('request');
request.get("https://moz.com/top500/domains/csv", function (error, response, body) {
    if (!error && response.statusCode == 200) {

    	var rows = body.split("\n");
    	for (var i = 1; i < rows.length - 1; i++) {
    		setTimeout(function(i) { 
    			return function() {
		    		var row = rows[i];
				    var columns = row.split(",");
				    var url = columns[1];
				    url = "http://www." + url.substring(1, url.length - 2);
				    extract_content_size(url, function(len) {
						for (var q = 0; q < len.length; q++) {
							var l = len[q];
							if (l == 0) {
								continue;
							}

							// Append to output
							fs.appendFile(outFile, l + "\n", function (err) {})
						}
					})
				}
			}(i), i * 1000);
		}
    }
});