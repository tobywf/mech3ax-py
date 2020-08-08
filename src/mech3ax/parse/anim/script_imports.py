# these imports are needed, because otherwise the classes wouldn't get picked up
# pylint: disable=unused-import
from .animation import DUMMY_IMPORT as _ANIMATION_DI
from .control_flow import DUMMY_IMPORT as _CONTROL_FLOW_DI
from .detonate_weapon import DUMMY_IMPORT as _DETONATE_WEAPON_DI
from .fog import DUMMY_IMPORT as _FOG_DI
from .frame_buffer_effects import DUMMY_IMPORT as _FBX_DI
from .light import DUMMY_IMPORT as _LIGHT_DI
from .object_motion import DUMMY_IMPORT as _OBJECT_MOTION_DI
from .object_motion_si_script import DUMMY_IMPORT as _OBJECT_MOTION_SI_DI
from .object_state import DUMMY_IMPORT as _OBJECT_STATE_DI
from .puffer import DUMMY_IMPORT as _PUFFER_DI
from .sequence import DUMMY_IMPORT as _SEQUENCE_DI
from .sound import DUMMY_IMPORT as _SOUND_DI

from .models import OBJECT_REGISTRY_NUM  # isort:skip

__all__ = ["OBJECT_REGISTRY_NUM"]
