"""Builder registry for plugin-style builder discovery."""

class BuilderRegistry:
    """Registry for discovering builders by type name.

    Builders register themselves via @register decorator.
    Factory looks up builders by name from config.
    """

    _builders = {}

    @classmethod
    def register(cls, builder_type: str):
        """Decorator to register a builder class.

        Usage:
            @BuilderRegistry.register("cross_tab")
            class CrossTabBuilder(MartBuilder):
                pass
        """

        def decorator(builder_class):
            cls._builders[builder_type] = builder_class
            return builder_class

        return decorator

    @classmethod
    def get(cls, builder_type: str):
        """Look up builder by type.

        Raises:
            ValueError: If builder type not found.
        """
        if builder_type not in cls._builders:
            available = ", ".join(sorted(cls._builders.keys()))
            raise ValueError(
                f"Unknown builder: {builder_type}. Available: {available}"
            )
        return cls._builders[builder_type]

    @classmethod
    def all(cls):
        """Return all registered builders."""
        return dict(cls._builders)
