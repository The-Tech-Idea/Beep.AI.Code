---
name: python-class
category: python
description: overridden
extension: .py
variables: class_name
---
class {class_name}:
    def __repr__(self): return "{class_name}"
