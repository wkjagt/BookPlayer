import time
import config
import RPi.GPIO as GPIO

class StatusLight(object):
  
    """available patterns for the status light"""
    patterns = {
        'on' : (.1, [True]),
        'off' : (.1, [False]),
        'blink_fast' : (.1, [False, True]),
        'blink' : (.1, [False, False, False, True, True, True, True, True, True, True, True, True, True]),
        'blink_pauze' : (.1, [False, False, False, False, False, False, False, False, False, False, False, False, False, False, True]),
    }

    """placeholder for pattern to tenmporarily interrupt
    status light with different pattern"""
    interrupt_pattern = [0, []]

    """continue flashing, controlled by the stop"""
    cont = True

    pin_id = None

    def __init__(self, pin_id):

        self.pin_id = pin_id
        GPIO.setmode(GPIO.BCM)

        GPIO.setup(pin_id, GPIO.OUT)
        self.action = 'on'
  
    def interrupt(self, action, repeat = 1):
        """Interupt the current status of the light with a names action
    
        parameters: action the name of the action
        repeat: the number of times to repeatthe interruption"""
        self.interrupt_pattern[0] = self.patterns[action][0]

        for i in range(0, repeat):
            self.interrupt_pattern[1].extend(list(self.patterns[action][1][:]))


    def start(self):
        """Perform a status light action"""

        while True:

            for state in self.patterns[self.action][1]:
                # if the interrupt_pattern is not empty, prioritize it
                while len(self.interrupt_pattern[1]):
                    time.sleep(self.interrupt_pattern[0])
                    self.set_state(state = self.interrupt_pattern[1].pop(0))

                # peform the regular action when not interrupted
                time.sleep(self.patterns[self.action][0])
                self.set_state(state)

    
    def set_state(self, state):
        """Turn the light on or off"""
        GPIO.output(self.pin_id, state)  
    
    def __del__(self):
        GPIO.cleanup()
    
    
if __name__ == '__main__':
    light = StatusLight(config.status_light_pin)
    light.interrupt('blink_fast', 3)
    light.start()
