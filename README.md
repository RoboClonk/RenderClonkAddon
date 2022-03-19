# RenderClonkAddon
An addon for Blender 3.0+ to import meshes/animations of the game LegacyClonk and Clonk Rage.
The addon contains a complete spritesheet renderer. Clonks, buildings, vehicles (etc.) can be rendered with animations onto a spritesheet.

## Installation
1. Go to the releases to get the latest stable version of the addon
or download the repository directly as zip-file
2. Install the addon like any other blender addon. 
  * You don't need to unzip the addon after you downloaded it and start blender
  * Navigate to 'Edit->Preferences...' then Select the tab 'Add-ons' in the new Window
  * Click on 'Install...' at the top right corner and browse to the zip-file via the filebrowser of Blender
  * Make sure the addon appears in the list and the checkbox on the left is checked.
![](https://github.com/RoboClonk/RenderClonkAddon/blob/main/TutorialPictures/RenderClonkEnabled.png?raw=true)

  * The addon can be found in the 3D View inside the properties panel (Open with 'N'). There is a Tab called Render Clonk
<img src="https://github.com/RoboClonk/RenderClonkAddon/blob/main/TutorialPictures/AddonTab.png" width="100">


## Examples

There is an [Examples Release](https://github.com/RoboClonk/RenderClonkAddon/releases/tag/Example) containing several example files that demonstrate the addon.



## Before Importing Clonks

If you want to import Clonk meshes, your folder structure can look like this: 

```python
     Clonk Content
           |
------------------------
|          |           |
Meshes     Actions     Tools
|
Textures
```

A few notes on this:
- The folder containing meshes should also contain a folder containing the face textures of the Clonks like FaceGob.png or the addon can't find and apply the textures on import. You can of course add these textures later manually or use different ones. I added new face textures in the [Examples Release](https://github.com/RoboClonk/RenderClonkAddon/releases/tag/Example) as well, which you can use.

* You can name these folders differently
* You can put everything in one folder (except textures, as mentioned) 
* You can add new folders

BUT the hierarchy should stay flat (don't use subfolders) otherwise the addon will not find actions or tools that belong to your meshes. I don't use recursive search in this addon to prevent it from accidentally searching through your entire file system.

AND you only need this for importing the meshes/tools/animations. All the necessary information will be saved inside the blend-file with the addon.





