#!/bin/bash
function npm_package_is_installed { #https://gist.github.com/JamieMason/4761049
  # set to 1 initially
  local return_=1
  # set to 0 if not found
  ls node_modules | grep $1 >/dev/null 2>&1 || { local return_=0; }
  # return value
  echo "$return_"
}

# Install mininet
hash mn 2>/dev/null || { 
	echo >&2 "Installing mininet";
	git clone git://github.com/mininet/mininet
	cd mininet
	git checkout 2.2.2
	cd ..
	mininet/util/install.sh -a
}

# Install python dependencies
sudo apt-get install python-numpy -y
sudo apt-get install python-matplotlib -y

# Install node
sudo apt-get install -y nodejs
sudo apt-get install -y npm
mkdir -p node_modules
if [ $(npm_package_is_installed request) == 0 ]
then
	npm install request
fi
if [ $(npm_package_is_installed cheerio) == 0 ]
then
	npm install cheerio
fi
if [ $(npm_package_is_installed url) == 0 ]
then
	npm install url
fi
if [ $(npm_package_is_installed csv-parser) == 0 ]
then
	npm install csv-parser
fi
if [ $(npm_package_is_installed node-async-loop) == 0 ]
then
	npm install node-async-loop
fi

# Run python
sudo python ./main.py

# Run node
nodejs scrape.js
python plot2.py

# Done
echo 'Complete! The results are stored in ./results/'
echo 'If anything went wrong or you have any questions, please contact me at samuco@stanford.edu'