class LicenseError(RuntimeError):
    """Base class for license failures safe to surface to the UI."""


class LicenseNetworkError(LicenseError):
    """The license server could not be reached."""


class LicenseServerError(LicenseError):
    """The license server rejected a request or returned invalid data."""


class LicenseSignatureError(LicenseError):
    """A signed license failed Ed25519 verification."""


class LicenseBindingError(LicenseError):
    """A license belongs to a different installation or device."""

