SubDebug
========
	Licence:			MIT (see acompanying "LICENCE")                       
	Description:		SubDebug is a package for Sublime Text for debugging  
						Lua script that incorporates MobDebug
						(https://github.com/pkulchenko/MobDebug)      
	Platform:			Sublime Text 3 (current development)                  
	Initiating author:	Abbey Games (www.abbeygames.com), Yuri van Geffen     
	
How to install
========
* Check out this repository to your package path, on Windows it will be something like this: `C:/Users/[NAME]/AppData/Roaming/Sublime Text 3/Packages/[CHOOSE A GOOD NAME, E.G. "subdebug"]`
* Pull the latest from master branch (this branch should always be operable).
* Check out the latest version of MobDebug (https://github.com/pkulchenko/MobDebug) and add it to your project.
* Add the following line to the beginning of your code:
```lua
mobdebug = require "[RELATIVE PATH TO mobdebug.lua]"
mobdebug.start()
```
* Start Sublime and set the base directory (SubDebug > Set base directory...). This is easier if you have your project opened as a folder in Sublime, because SubDebug will suggest appropriate paths.
* You are ready to start debugging your code with SubDebug. Run your script! If you have SubDebug > Step on Connect enabled, your script  will halt on connection and you can step through your code. If you have breakpoints set, your script will halt there too.

Pitfalls
========
* Watch out, when (re)setting your base directory, all breakpoints will reset!
* MobDebug isn't the fastest script in the world. If your application runs too slow, consider turning debugging off and on in specific area's by calling `mobdebug.off()` and `mobdebug.on()` in your code.
