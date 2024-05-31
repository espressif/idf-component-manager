# Test Components

The components under this folder would be uploaded to the ESP Component Registry under namespace `test`. Would be used
for testing with the following scenarios.

## Scenarios

### Circular Dependency

```mermaid
graph LR
  R[root]
  A1[a <1.0.0>]
  A2[a <2.0.0>]
  B1[b <1.0.0>]

  R -- a: >=1.0.0 --> A1
  R -- a: >=1.0.0 --> A2

  A2 -- b: ^1.0.0 --> B1

  B1 -- a: ^1.0.0 --> A1
```

a <1.0.0>

### Diamond Dependency

```mermaid
graph LR
  R[root]
  A1[a <1.0.0>]
  A2[a <2.0.0>]
  B1[b <1.0.0>]
  B2[b <2.0.0>]
  C1[c <1.0.0>]
  C2[c <2.0.0>]
  C3[c <3.0.0>]

  R -- a: * --> A1
  R -- a: * --> A2

  R -- b: * --> B1
  R -- b: * --> B2

  A2 -- c: ^1.0.0 --> C1

  B1 -- c: ^2.0.0 --> C2
  B2 -- c: ^3.0.0 --> C3
```

a <1.0.0> b <2.0.0> c <3.0.0>

### Jump Back After Partially Satisfied

```mermaid
graph LR
  R[root]
  A1[a <1.0.0>]
  B1[b <1.0.0>]
  C1[c <1.0.0>]
  C2[c <2.0.0>]
  X0[x <0.0.0>]
  X1[x <1.0.0>]
  X2[x <2.0.0>]
  Y1[y <1.0.0>]
  Y2[y <2.0.0>]

  R -- c: * --> C1
  R -- c: * --> C2
  R -- y: ^2.0.0 --> Y2

  A1 -- x: >=1.0.0 --> X1
  A1 -- x: >=1.0.0 --> X2

  B1 -- x: <2.0.0 --> X0
  B1 -- x: <2.0.0 --> X1

  C2 -- a: * --> A1
  C2 -- b: * --> B1

  X1 -- y: ^1.0.0 --> Y1
```

c <1.0.0> y <2.0.0>

### Roll Back the Further the Earlier

```mermaid
graph LR
  R[root]
  A1[a <1.0.0>]
  A2[a <2.0.0>]
  B1[b <1.0.0>]
  B2[b <2.0.0>]
  C1[c <1.0.0>]
  C2[c <2.0.0>]

  R -- a: * --> A1
  R -- a: * --> A2

  A1 -- b: * --> B1
  A1 -- b: * --> B2

  A2 -- b: * --> B1
  A2 -- b: * --> B2
  A2 -- c: ^2.0.0 --> C2

  B2 -- c: ^1.0.0 --> C1
```

a <2.0.0> b <1.0.0> c <2.0.0>
