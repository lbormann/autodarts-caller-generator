# AUTODARTS-CALLER-GENERATOR
[![Downloads](https://img.shields.io/github/downloads/lbormann/autodarts-caller-generator/total.svg)](https://github.com/lbormann/autodarts-caller-generator/releases/latest)





## INSTALL INSTRUCTION


### Desktop-OS / Headless-OS:

- Download the appropriate executable in the release section.


### By Source:

#### Setup python3

- Download and install python 3.x.x for your specific os.
- Download and install pip.


#### Get the project

    git clone https://github.com/lbormann/autodarts-caller-generator.git

Go to download-directory and type:

    pip3 install -r requirements.txt





## SETUP

autodarts-caller-generator uses service providers like google and amazon (aws) to generate sound-file-packages. In order to use these providers you need to setup credentials.



## RUN IT

You can run by source or run an os specific executable.


### Run by executable

#### Example: Windows 

Create a shortcut of the executable; right click on the shortcut -> select properties -> add [Arguments](#Arguments) in the target input at the end of the text field.

Example: C:\Downloads\autodarts-caller-generator.exe -TP "absolute-path-to-your-template-files" -GP "absolute-path-to-your-generation-directory" -GRP "absolute-path-to-your-generation-raw-directory"

Save changes.
Click on the shortcut to start the application.


### Run by source

#### Example: Linux

Copy the default script:

    cp start.sh start-custom.sh

Edit and fill out [Arguments](#Arguments):

    nano start-custom.sh

Make it executable:

    chmod +x start-custom.sh

Start the script:

    ./start-custom.sh



### Arguments

- -TP / --templates_path
- -GP / --generation_path
- -GPR / --generation_path_raw


*`-TP / --templates_path`*

You need to set an absolute path to your template-file-directory. Moreover make sure the given path doesn't reside inside main-directory (autodarts-name-grabber).

*`-GP / --generation_path`*

You need to set an absolute path to your generation-directory. Moreover make sure the given path doesn't reside inside main-directory (autodarts-name-grabber).

*`-GRP / --generation_raw_path`*

You need to set an absolute path to your generation-raw-directory. Moreover make sure the given path doesn't reside inside main-directory (autodarts-name-grabber).




## BUGS

It may be buggy. I've just coded it for fast fun with https://autodarts.io. You can give me feedback in Discord > wusaaa


## TODOs

### Done

- Init project



## LAST WORDS

Thanks to Timo for awesome https://autodarts.io. It will be huge!

