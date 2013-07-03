import time
import config

class StatusLight(object):
  
	"""available patterns for the status light"""
	patterns = {
		'blink_fast' : (.1, [False, True]),
		'blink' : (.5, [False, True]),
	}

	"""placeholder for pattern to tenmporarily interrupt
	status light with different pattern"""
	interrupt_pattern = [0, []]
	
	"""continue flashing, controlled by the stop"""
	cont = True

	def __init__(self, pin_id):

		GPIO.setmode(GPIO.BCM)

		GPIO.setup(pin_id, GPIO.OUT)
		# GPIO.output(self.status_light_pin, True)


	
	def interrupt(self, action, repeat = 1):
		"""Interupt the current status of the light with a names action
		
		parameters: action the name of the action
		            repeat: the number of times to repeatthe interruption"""
		self.interrupt_pattern[0] = self.patterns[action][0]

		for i in range(0, repeat):
			self.interrupt_pattern[1].extend(list(self.patterns[action][1][:]))



	def do(self, action):
		"""Perform a status light action
		
		paramaters: action: the name of tehe action"""
		
		if(len(self.interrupt_pattern[1])):
			# if the interrupt_pattern is not empty, prioritize it
			time.sleep(self.interrupt_pattern[0])
			self.set_state(self.interrupt_pattern[1].pop(0))
			return self.do(action)

		for state in self.patterns[action][1]:
			# peform the regular action when not interrupted
			time.sleep(self.patterns[action][0])
			self.set_state(state)
		
		if self.cont:
			# continue of not stopped
			self.do(action)
		
	def off(self, state):
		"""Turn off status light"""
		self.cont = False
		self.set_state(state)
		
	def set_state(self, state):
		"""Turn the light on or off"""
		print 'set state to %s' % state	
		
		
		
		
if __name__ == '__main__':
	light = StatusLight(config.status_light_pin)
	light.interrupt('blink_fast', 3)
	light.do('blink')
