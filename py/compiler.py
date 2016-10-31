import sys
import json
import tokenizer
import pprint

Reader = tokenizer.Reader

def translate_crawl(ast, handler):
	for item in ast:
		# If the handler does not prohibit transversal
		# by returning True then traverse into any known
		# sub-elements.
		if handler(item) is not True:
			if 'body' in item:
				translate_crawl(item['body'], handler)
			if 'cond_true' in item:
				translate_crawl(item['cond_true'], handler)
			if 'cond_false' in item:
				translate_crawl(item['cond_false'], handler)

def load_iden(iden, out):
	parts = iden.split('.')

	if len(parts) == 0:
		raise Exception('[bug] strange condition; fatal error')

	if len(parts) == 1:
		out.append(('load.local', iden))
		return

	out.append(('load.local', parts[0]))

	for part in parts[1:]:
		# The opcode says to use the item on the top of
		# the stack as an object which holds the member
		# specified by the following instruction and to
		# load that member onto the stack while also consuming
		# the top of the stack item in the process.
		out.append(('load.member', part))

	# Effectively, the identifier `apple.grape.peach' would
	# first load the local `apple` onto the stack then load the
	# member `grape` from `apple` consuming `apple` on the stack
	# and finally load the member `peach` and once again consuming
	# the item on top of the stack leaving the object represented
	# by `apple.grape.peach`.
	return

def store_to_something(something, out):
	"""
	Store one or more values onto the stack into locals.

	This is a helper primarily for handling cases where:

	(1) output is a single variable
	(2) output is from a tuple type to multiple variables
	(3) output form is not recognized
	"""

	if type(something) is list:
		out.append(('tuple.unpack', len(something)))
		for o in something:
			if len(o) != 1 or o[0]['xtype'] != 'is_name':
				raise Exception('Expected a identifier for tuple output element.')
			out.append(('store.local', o[0]['value']))
	elif type(something) is str:
		out.append(('store.local', something))
	else:
		raise Exception('Not able to handle assignment to something not tuple like or single variable.')

def translate_seq(seq):
	body = Reader(seq)

	out = []

	def load_something(something):
		if something['xtype'] == 'is_name':
			load_iden(something['value'], out)
			# The name can have dots like `apple.member`, therefore,
			# this needs to be parsed and the appropriate byte-code
			# emitted to access members at any depth.
			#out.append(('load.local', something['value']))
		elif something['xtype'] == 'is_number':
			out.append(('load.num', something['value']))
		elif something['xtype'] == 'is_string':
			out.append(('load.string', something['value']))
		elif something['xtype'] == 'is_invocation':
			# The first input should already be on
			# the stack after the invocation completes.
			out.append(something)
		elif something['xtype'] == 'is_subexpression':
			# The first input should already be on
			# the stack.
			out.append(something)
		else:
			# Unknown
			raise Exception('Compiler problem handling first item of AST assignment as %s' % something)

	first = body.one()
	load_something(first)

	delayed_cmp_op = None

	valid_cmp_types = [
		'is_greater',
		'is_less',
		'is_equal',
		'is_eq_or_greater',
		'is_eq_or_less',
	]

	def do_comparison(cmp_type):
		if cmp_type == 'is_greater':
			out.append(('cmp.greater',))
		elif cmp_type == 'is_less':
			out.append(('cmp.less',))
		elif cmp_type == 'is_equal':
			out.append(('cmp_equal',))
		elif cmp_type == 'is_eq_or_greater':
			out.append(('cmp_eq_or_greater',))
		elif cmp_type == 'is_eq_or_less':
			out.append(('cmp_eq_or_less',))
		else:
			raise Exception('The comparison type was not understood.')

	while body.has_more():
		a = body.one()
		b = body.one()

		load_something(b)

		if a['xtype'] == 'is_add':
			out.append(('math.add',))
		elif a['xtype'] == 'is_sub':
			out.append(('math.sub',))
		elif a['xtype'] == 'is_mul':
			out.append(('math.mul',))
		elif a['xtype'] == 'is_div':
			out.append(('math.div',))
		elif a['xtype'] == 'is_mod':
			out.append(('math.mod',))
		elif a['xtype'] in valid_cmp_types:
			# At this point, leave currently computed value
			# on the stack and start a new computation but
			# once end of expression or new comparison is reached
			# then do the comparison.
			if delayed_cmp_op is not None:
				cmp_op = delayed_cmp_op
				delayed_cmp_op = None
				do_comparison(cmp_op)

			delayed_cmp_op = a['xtype']
		else:
			raise Exception('The expected operation %s is not understood.' % b)

	# This happened because of the need to fully evaluate
	# both sides of the comparison operation. When this comparison
	# token was found the expression calculation left the currently
	# calculated left side and started on the right side and at this
	# point the left side value and right side value are on the stack.
	if delayed_cmp_op is not None:
		do_comparison(delayed_cmp_op)

	return out

def translate(ast):
	'''
		This function at first will do the bulk of translation
		to byte-code but many critical structures will be left
		such as loops, if statements, and function invocations. 
		This bulk is mainly sequential expressions and does not
		include control elements and function calls.

		The second phase is to start to deconstruction the AST
		tree, with the now added byte-code, from the top down. 
		This is akin to collapsing the tree from the top down
		so that ultimately all that is left is a single one
		dimensional array/list of byte-code and possibly some
		single level deep special tokens. In this second phase,
		the control flow (if statements, loops, and invocations)
		will have byte-code emitted tying everything together.
	'''

	def handler(item):
		#
		# The bytecode that gets emitted here is likely to get walked
		# over and passed into this handler. Since it is a tuple type
		# it can be easily eliminated; however, I am unsure if making
		# the bytecode elements a tuple instead of a dict with an xtype
		# was a wise decision.
		#

		if type(item) is dict and item['xtype'] == 'is_subexpression':
			item['body'] = translate_seq(item['body'])

		if type(item) is dict and 'cond' in item:
			item['cond'] = translate_seq(item['cond'])

		if type(item) is dict and item['xtype'] == 'is_invocation':
			args = item['args']

			for x in range(0, len(args)):
				args[x] = translate_seq(args[x])

		if type(item) is dict and item['xtype'] == 'is_stmt_return':
			print('body', item['body'])
			item['body'] = translate_seq(item['body'])			

		if type(item) is dict and item['xtype'] == 'is_stmt_assignment':
			item['body'] = translate_seq(item['body'])
			# Now that the byte-code to calculate the expression has
			# been generated the output needs to be stored if specified.
			if 'dst' in item and item['dst'] is not None:
				store_to_something(item['dst'], item['body'])
			else:
				# If not stored then it shall simply be poped from the
				# stack. This is done because the calculation of the
				# expression could have had side-effects (a good thing 
				# if intended by the programmer; likely), therefore, the
				# output of the expression is simply ignored by popping
				# it from the stack.
				item['body'].append(('stack.pop.one',))

	# The first phase. No collapsing of AST. Bulk translation.
	translate_crawl(ast, handler)

	def handler_phase_two_collapse(item, out):
		if type(item) is tuple:
			# This is a byte-code, but I do not like how I am
			# using the type tuple to determine this; however,
			# at the moment it is a quick and dirty way to do
			# it to get this project done.
			#
			# TODO: make byte-code tokens dict types with xtype
			#       field set to `bytecode`.
			#
			out.append(item)
			return

		if item['xtype'] == 'is_stmt_if':
			# Bring down the evaluation section of byte-code.
			for sitem in item['cond']:
				handler_phase_two_collapse(sitem, out)
			true_cond = []
			for sitem in item['cond_true']:
				handler_phase_two_collapse(sitem, true_cond)
			false_cond = []
			for sitem in item['cond_false']:
				handler_phase_two_collapse(sitem, false_cond)
			# Add control-flow logic using offset calculated
			# by length of true_cond block. 
			#
			for sitem in true_cond:
				if type(sitem) is not tuple:
					raise Exception('Expected all byte-code.\n%s' % sitem)
			for sitem in false_cond:
				if type(sitem) is not tuple:
					raise Exception('Expected all byte-code.\n%s' % sitem)

			# If result on top of stack is false then jump over
			# the true_cond block of byte-code.
			out.append(('flow.reljmpfalse', len(true_cond) + 2))
			# Emit true_cond block and then emit jump over
			# the false_cond block.
			for sitem in true_cond:
				out.append(sitem)
			if len(false_cond) > 0:
				out.append(('flow.reljmp', len(false_cond) + 1))
				for sitem in false_cond:
					out.append(sitem)
			# Now matter the path, execution should be here now
			# if this byte-code was executed. This IF statement
			# has been collapsed and through recursion any inner
			# IF statements or other tokens shall have been
			# collapsed.
		elif item['xtype'] == 'is_stmt_assignment':
			for sub_item in item['body']:
				handler_phase_two_collapse(sub_item, out)
		elif item['xtype'] == 'is_subexpression':
			for sub_item in item['body']:
				handler_phase_two_collapse(sub_item, out)
		elif item['xtype'] == 'is_invocation':
			# Place each argument expression onto the stack.
			for arg in item['args']:
				for sub_item in arg:
					handler_phase_two_collapse(sub_item, out)
			# Emit byte-code instruction for invocation.
			#
			# (1) It may reference a local and members.
			#		Indirect: invocation of method of object.
			# (2) It may reference an accessible type and
			#     subsequent static member(s). 
			#       Direct: static reference.
			# (3) It may reference a local method. (direct)
			#       Direct: static reference
			#
			# The process which translate the byte-code into
			# native code will handle this determination, or
			# the interpreter will handle it during execution.
			#
			ref = '.'.join(item['name_parts'])
			out.append(('invoke', ref, len(item['args'])))
		elif item['xtype'] == 'is_stmt_dec':
			# TODO: implement this
			pass
		elif item['xtype'] == 'is_stmt_return':
			for sitem in item['body']:
				handler_phase_two_collapse(sitem, out)
			out.append(('return',))
		else:
			raise Exception('[bug] If type is not tuple, then it should have been something collapsed. The type was %s:\n%s' % (item['xtype'], item))


	def handler_phase_two_search(item):
		if item['xtype'] == 'is_stmt_fn':
			# Collapse each element if not a byte-code
			# element so that only a sequence of byte-codes
			# and any special tokens are remaining.
			body = item['body']
			out = []

			for x in range(0, len(body)):
				handler_phase_two_collapse(body[x], out)

			item['body'] = out

			# stop transversal
			return True

	translate_crawl(ast, handler_phase_two_search)

	# The second phase. Collapsing of AST from top down. The
	# generation of byte-code for control flow and method invocation.
	pprint.pprint(ast)

	print('SECOND-PHASE-NOT-IMPLEMENTED-YET')

def main():
	data = sys.stdin.read()

	inplist = data.split('\n')

	on = False

	for inp in inplist:
		if not on:
			if inp == '---start---':
				on = True
			continue

		if len(inp) == 0:
			continue

		inp = json.loads(inp)

		translate(inp)


if __name__ == '__main__':
	main()