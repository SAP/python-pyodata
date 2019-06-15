Function imports
================

Calling a function import
-------------------------

.. code-block:: python

    products = northwind.functions.GetProductsByRating.parameter('rating', 16).execute()

    for prod in products:
        print(prod)
