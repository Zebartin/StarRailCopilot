import cv2
from scipy import signal

from module.base.timer import Timer
from module.base.utils import rgb2luma
from module.logger import logger
from tasks.base.ui import UI
from tasks.combat.assets.assets_combat_state import *


class CombatState(UI):
    _combat_click_interval = Timer(2, count=4)
    _combat_enter_timer = Timer(1, count=3)
    _combat_auto_checked = False
    _combat_2x_checked = False
    # gray scale image or None
    _combat_damage_image = None

    def is_combat_executing(self) -> bool:
        appear = self.appear(COMBAT_PAUSE)
        if appear:
            if COMBAT_PAUSE.button_offset[0] < 3:
                return True

        return False

    def _is_combat_button_active(self, button):
        image = rgb2luma(self.image_crop(button, copy=False))
        lines = cv2.reduce(image, 1, cv2.REDUCE_AVG).flatten()
        # [122 122 122 182 141 127 139 135 130 135 136 141 147 149 149 150 147 145
        #  148 150 150 150 150 150 144 138 134 141 136 133 173 183 130 128 127 126]
        parameters = {
            # Border is about 188-190
            'height': 96,
            # Background is about 120-122
            'prominence': 35,
            'width': (0, 7),
            'distance': 7,
        }
        peaks, _ = signal.find_peaks(lines, **parameters)
        count = len(peaks)
        if count == 0:
            return False
        elif count == 2:
            return True
        else:
            # logger.warning(f'Unexpected peak amount on {button}: {count}, lines={lines}')
            # self.device.image_save()
            return False

    def is_combat_auto(self) -> bool:
        return self._is_combat_button_active(COMBAT_AUTO)

    def is_combat_speed_2x(self) -> bool:
        return self._is_combat_button_active(COMBAT_SPEED_2X)

    def combat_state_reset(self):
        self._combat_auto_checked = False
        self._combat_2x_checked = False
        self._combat_click_interval.clear()
        # Game client does not response to COMBAT_AUTO clicks at the very beginning
        self._combat_enter_timer.reset()
        # clear cache
        self._combat_damage_image = None

    def handle_combat_state(self, auto=True, speed_2x=True):
        """
        Set combat auto and 2X speed. Enable both by default.

        Returns:
            bool: If clicked
        """
        if self._combat_auto_checked and self._combat_2x_checked:
            return False
        if not self.is_combat_executing():
            if not self._combat_auto_checked and auto:
                # >=0.2s after clicking the button to avoid random noice
                if self._combat_click_interval.current() >= 0.15 and not self._combat_click_interval.reached():
                    logger.info('Combat on going, _combat_auto_checked')
                    self._combat_auto_checked = True
            return False

        if not self._combat_2x_checked:
            if speed_2x:
                if self.is_combat_speed_2x():
                    logger.info('_combat_2x_checked')
                    self._combat_2x_checked = True
                else:
                    if self._combat_enter_timer.reached() and self._combat_click_interval.reached():
                        self.device.click(COMBAT_SPEED_2X)
                        self._combat_click_interval.reset()
                        return True
            else:
                if self.is_combat_speed_2x():
                    if self._combat_enter_timer.reached() and self._combat_click_interval.reached():
                        self.device.click(COMBAT_SPEED_2X)
                        self._combat_click_interval.reset()
                        return True
                else:
                    logger.info('_combat_2x_checked')
                    self._combat_2x_checked = True

        if not self._combat_auto_checked:
            if auto:
                if self.is_combat_auto():
                    logger.info('_combat_auto_checked')
                    self._combat_auto_checked = True
                else:
                    if self._combat_enter_timer.reached() and self._combat_click_interval.reached():
                        self.device.click(COMBAT_AUTO)
                        self._combat_click_interval.reset()
                        return True
            else:
                if self.is_combat_auto():
                    if self._combat_enter_timer.reached() and self._combat_click_interval.reached():
                        self.device.click(COMBAT_AUTO)
                        self._combat_click_interval.reset()
                        return True
                else:
                    logger.info('_combat_auto_checked')
                    self._combat_auto_checked = True

        return False

    def handle_combat_damage_change(self):
        """
        Watch combat damage changes
        If damage changed, we consider combat is still ongoing

        Returns:
            bool: If changed
        """
        # must have damage numbers
        if not self.image_color_count(COMBAT_DAMAGE, color=(255, 255, 180), threshold=221, count=100):
            return False

        image = self.image_crop(COMBAT_DAMAGE, copy=False)
        image = rgb2luma(image)
        if self._combat_damage_image is None:
            # new image
            self._combat_damage_image = image
            return True
        else:
            # existing image, try if changed
            res = cv2.matchTemplate(self._combat_damage_image, image, cv2.TM_CCOEFF_NORMED)
            _, sim, _, _ = cv2.minMaxLoc(res)
            # logger.info(sim)
            if sim <= 0.75:
                self._combat_damage_image = image
                return True
            else:
                return False
