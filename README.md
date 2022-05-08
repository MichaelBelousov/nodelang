
# nodelang

An almost completely unimplemented language for parity with node graphs, particularly targetting blender's material and geometry node graphs.


## ideas

- immutable expressions can be out of order
- reroute nodes are variables
- comments are variables
- use single quotes to delimit variables? (to allow for arbitrary text for variable names)
- arrays of size 4 or less automatically have the rgba and xyzw swizzle attributes ala GLSL
- you can sync node graphs
- needs to have a graph layout algorithm for generating a graph from text rather than syncing
- needs to have deterministic automatic naming for node graphs
- maybe fold symmetric expressions
- need an isomorphism for groups but still with the ability to access variables between them

## samples

```nodelang

struct Context {
  textureCoordinate: {
    generated: f32[4],
    uv: f32[2],
  }
}

struct Result {
  surface: ?BSDF,
  volume: ?BSDF,
}

fn SubGraph(a: i32[4], b: b1[4]) f32[2] {
  /// group: 1
  // regular comment
  const simpleVariable = 52.f;
  const 'long variable' = 10.f;
  const 'eye length' = atan2('var ref', simpleVariable);
  /// end group
  
  /// group: group with a more interesting comment
  const 'var ref' = 'long variable' * a; // referenced above
  /// end group

  // OR

  group X {
    const 'my var' = 5f;
  }

  group Y {
    const 'my var' = 10u32 + X.'my var'
  }
}

fn main(ctx: Context) Result {
  return Result {
    .surface = Glossy * SubGraph(ctx.uv ++ ctx.uv, {true, false ,false, false});
  };
}


```

## alternative

Perhaps to best be isomorphic with node trees, a lisp dialect is in order... sounds unpopular though

```nodelang-lisp
; look at this cute `.property` shorthand syntax for building objects. I wonder how other lisps do it
(material-out
  (.surface
    (principled-bsdf (.albedo (+ #ff23ab
                                 uv.blah)))
  )
)
```

Another option is to keep infix binary operators but format them like trees:

```nodelang-binop

fn main(ctx: Context) Result {
  Result result;
  result.surface = PrincipledBsdf(
    albedo=   #ff23ab
            + uv.blah
  );
}

```

## Development

### blender bpy analysis in VSCode

First, find the path of the modules folder for your blender install. You can find it by running
this python in Blender's python console

```python
import bpy
bpy.__file__
```

Then, to get intellisense in vscode for blender, add following snippet to your `settings.json`, but with the path to `modules` you found.

```json
{
  "python.analysis.extraPaths": ["/snap/blender/2106/3.1/scripts/modules"]
}
```
