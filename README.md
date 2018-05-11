## Notifier
<img align="left" style="float: left; padding-right: 20px" src="https://i.imgur.com/dPgfW1G.png"> This will one day be the grounds for a more robust notification system. For now, the only example I have is to warn you if your autokey is OFF. Helpful for animators that like using StudioLibrary or other tools that mess with autokey.

---
**[Installation](#installation)**

Place the notifier.py file in your maya/scripts folder. 
The other files do not matter.

```
~maya/scripts/
            - notifier.py

```

---
**[Usage](#usage)**

To activate the notifier, make this a <b>python</b> button on your shelf.
```
# Turn it on
import notifier
notifier.activate()
```

To deactivate the notifier, make this a <b>python</b> button on your shelf.
```
# Turn it off
notifier.deactivate()
```


