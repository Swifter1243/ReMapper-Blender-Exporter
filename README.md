# What Is This?
ReMapper Blender Exporter is a companion [Blender](https://www.blender.org/) plugin for [ReMapper](https://github.com/Swifter1243/ReMapper) models. It specifically focuses on the [ModelScene](https://github.com/Swifter1243/ReMapper/wiki/Model-Scene) implementation, but the exporter exports objects to `.rmmodel` files in a very general format, representing their positions in the scene.

<ins>The exporter is not a requirement for anything Unity related</ins>, as this is mostly intended for [geometry/environment](https://github.com/Aeroluna/Heck/wiki/Environment) statements. 

# What Version to Use
Different versions of ReMapper work with different versions of the exporter. Here's how:

| Exporter Version | ReMapper Version | File Format Version |
|---|---|---|
| 0.01...0.03 | 3.0.0 | v1 |
| 0.04...0.05 | 3.1.0 | v1 |
| 0.06 | 4.0.0 | v2 |

# Installation
Go to releases, download the `script.py` from the release you want, and put it somewhere in your computer.

In Blender, open `Edit > Preferences > Add-ons > Install` and navigate to the `script.py`.

Make sure to enable the plugin after installing. After expanding a part of the UI on the side, a tab should show up called `RM Exporter`.

<img src="https://user-images.githubusercontent.com/90769470/185506952-71625260-b2fb-46c4-b147-bb332c532cbe.png" alt="screenshot" width="500"/>
<img src="https://user-images.githubusercontent.com/61858676/183328172-f9cb8533-6dc3-4363-a5cc-70340d3cb1bf.jpg" alt="screenshot" width="500"/>

# File Format Versions

Here's what a `.rmmodel` file looks like:

### v1
```ts
{
  "objects": [
    ...
    {
      "pos": [x, y, z] | [[x, y, z, t], ...],
      "rot": [x, y, z] | [[x, y, z, t], ...],
      "scale": [x, y, z] | [[x, y, z, t], ...],
      "track": string,
      "color": [r, g, b, a]
    }
    ...
  ]
}
```

### v2
```ts
{
  "version": 2,
  "objects": [
    ...
    {
      "position": [x, y, z] | [[x, y, z, t], ...],
      "rotation": [x, y, z] | [[x, y, z, t], ...],
      "scale": [x, y, z] | [[x, y, z, t], ...],
      "group": string,
      "color": [r, g, b, a]
    }
    ...
  ]
}
```

### Interpretation
`position/rotation/scale` represent the transformation of an object based on it's origin. It's essentially what you see in the "Item" tab, but transformed into Unity's world space.

![image](https://github.com/user-attachments/assets/2d0ac6d3-2209-4750-b96d-912b29ecf249)

For any of these given transformation properties, they may either be **simple** or **complex** depending on whether they change throughout the animation:
- **Simple**: `[x, y, z]` This is an array of `xyz` values that stay the same the entire animation.
- **Complex**: `[[x, y, z, t], ...]` An array of arrays with `xyz` and `t` values, where each inner array is a "keyframe". `t` represents the percentage into the animation that the keyframe takes place.

`group` is a string that is taken from the object's first material name.

`color` is based on `Object > Viewport Display > Color`. This is to allow objects to have the same material/group while having unique colors.

![image](https://github.com/user-attachments/assets/d78d9eab-afd4-41e4-8017-9055a4d98740)

# Usage

When you are looking at the plugin panel, you'll see a bunch of fields/buttons:

![image](https://github.com/user-attachments/assets/6340077b-1bc2-4d51-b80b-37cbe5ae84c1)

- **Show Object Color** - Switches your viewport to display object color instead of material color. [As explained here](Interpretation), it's what's used to actually export the `color` property.

- **File Name** - The location of the export. Relative paths are relative to the location of the `.blend`.
  * Tip: If left blank, it will be exported to a file in the same directory as your `.blend`, with the name of the current Blender scene. This particular feature is useful for having a `.blend` file contain multiple scenes with different environments, each exporting to their own `.rmmodel`.
- **Only Selected** - Whether to only export objects in the current selection.
- **Export Animations** - Whether to export objects as animated or use only the first frame of the animation.
- **Sample Rate** - If `Export Animations` is enabled, the rate to sample the animation keyframes. For example, `1` will export every frame, `2` will export every second frame, `3` will export every third.. etc. The last frame is gauranteed to be sampled, though.
- **Export** - Export the model.
