import django
if django.VERSION < (1, 6):
    from .fixtures import FixtureTests
    from .forms import (BasicProxyFormTest, BasicCompoundFormTest,
                        LinkedCompoundFormTest)
    from .formsets import (ProxyFormSetTests, CompoundInlineFormSetTests)