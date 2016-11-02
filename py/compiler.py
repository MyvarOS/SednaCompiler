import sys
import json
import tokenizer
import pprint

Reader = tokenizer.Reader


def one_level_collapse(inp):
	out = []
	for si in inp:
		if type(si) is list:
			for ni in si:
				if type(ni) is tuple:
					out.append(ni)
				else:
					if ni.get('final_bytecode', 'error') == 'error':
						pprint.pprint(ni)
						raise Exception('error')
					bc = ni['final_bytecode']
					for zi in bc:
						if type(zi) is not tuple:
							pprint.pprint(zi)
							raise Exception('expected bytecode')
						out.append(zi)
		else:
			if type(si) is tuple:
				out.append(si)
			else:
				if si['xtype'] in tmap_ignore:
					continue
				bc = si['final_bytecode']
				for zi in bc:
					if type(zi) is not tuple:
						pprint.pprint(zi)
						raise Exception('expected bytecode')
					out.append(zi)
	return out

class Token:
	def __init__(self):
		raise Exception('!')
	def get_translate_asts(self):
		raise Exception('%s.get_translate_asts not implemented' % type(self))
	def translate_sequences(self):
		raise Exception('%s.translate_sequences not implemented' % type(self))

class TokenStmtReturn(Token):
	def __init__(self, data):
		self.data = data
		self.bc = None
	def get_translate_asts(self):
		return [self.data['body']]
	def translate_sequences(self):
		self.data['bytecode'] = translate_seq(self.data['body'])
		self.data['bytecode'].append(('return',))
	def collapse(self):
		self.data['final_bytecode'] = one_level_collapse(self.data['bytecode'])

class TokenStmtFn(Token):
	def __init__(self, data):
		self.data = data
	def get_translate_asts(self):
		return [self.data['body']]
	def translate_sequences(self):
		return
	def collapse(self):
		self.data['final_bytecode'] = one_level_collapse(self.data['body'])
		self.data['body'] = None

class TokenComment(Token):
	def __init__(self, data):
		self.data = data
	def get_translate_asts(self):
		return []
	def translate_sequences(self):
		return
	def collapse(self):
		self.data['final_bytecode'] = []

class TokenStmtScope(Token):
	def __init__(self, data):
		self.data = data
	def get_translate_asts(self):
		return []
	def translate_sequences(self):
		return
	def collapse(self):
		self.data['final_bytecode'] = []

class TokenAttribute(Token):
	def __init__(self, data):
		self.data = data
	def get_translate_asts(self):
		return []
	def translate_sequences(self):
		return
	def collapse(self):
		self.data['final_bytecode'] = []

class TokenStmtType(Token):
	def __init__(self, data):
		self.data = data
	def get_translate_asts(self):
		return [self.data['body']]
	def translate_sequences(self):
		return
	def collapse(self):
		return

class TokenStmtIf(Token):
	def __init__(self, data):
		self.data = data
		self.final_bytecode = None
	def get_translate_asts(self):
		return [
			self.data['cond'],
			self.data['cond_true'],
			self.data['cond_false'],
		]
	def translate_sequences(self):
		self.data['cond-bytecode'] = translate_seq(self.data['cond'])
		#self.data['cond_true-bytecode'] = translate_seq(self.data['cond_true'])
		#self.data['cond_false-bytecode'] = translate_seq(self.data['cond_false'])

	def collapse(self):
		cond_bytecode = one_level_collapse(self.data['cond-bytecode'])
		cond_true_bytecode = one_level_collapse(self.data['cond_true'])
		cond_false_bytecode = one_level_collapse(self.data['cond_false'])

		fbc = []

		for i in cond_bytecode:
			fbc.append(i)
		fbc.append(('flow.reljmpfalse', len(cond_true_bytecode) + 1))
		for i in cond_true_bytecode:
			fbc.append(i)
		if len(cond_false_bytecode) > 0:
			fbc.append(('flow.reljmp', len(cond_false_bytecode) + 1))
			for i in cond_false_bytecode:
				fbc.append(i)

		self.data['final_bytecode'] = fbc

class TokenInvocation(Token):
	def __init__(self, data):
		self.data = data
	def get_translate_asts(self):
		return []
	def translate_sequences(self):
		self.data['args_bytecode'] = []

		for arg in self.data['args']:
			self.data['args_bytecode'].append(translate_seq(arg))
	def collapse(self):
		fbc = []

		for arg in self.data['args_bytecode']:
			arg = one_level_collapse(arg)
			for i in arg:
				fbc.append(i)

		ref = '.'.join(self.data['name_parts'])
		fbc.append(('invoke', ref, len(self.data['args_bytecode'])))

		self.data['final_bytecode'] = fbc

class TokenStmtThrow(Token):
	def __init__(self, data):
		self.data = data
	def get_translate_asts(self):
		return [self.data['exp']]
	def translate_sequences(self):
		self.data['exp-bytecode'] = translate_seq(self.data['exp'])
	def collapse(self):
		self.data['final_bytecode'] = one_level_collapse(self.data['exp-bytecode'])
		self.data['final_bytecode'].append(('throw',))

class TokenStmtAssignment(Token):
	def __init__(self, data):
		self.data = data
	def get_translate_asts(self):
		return [self.data['body']]
	def translate_sequences(self):
		self.data['body-bytecode'] = translate_seq(self.data['body'])
	def collapse(self):
		fbc = []
		self.data['body-bytecode'] = one_level_collapse(self.data['body-bytecode'])
		for i in self.data['body-bytecode']:
			fbc.append(i)
		store_to_something(self.data['dst'], fbc)
		self.data['final_bytecode'] = fbc

class TokenSubExpression(Token):
	def __init__(self, data):
		self.data = data
	def get_translate_asts(self):
		return [self.data['body']]
	def translate_sequences(self):
		self.data['body-bytecode'] = translate_seq(self.data['body'])
	def collapse(self):
		self.data['final_bytecode'] = one_level_collapse(self.data['body-bytecode'])

class TokenIndex(Token):
	def __init__(self, data):
		self.data = data
	def get_translate_asts(self):
		return [self.data['exp']]
	def translate_sequences(self):
		self.data['exp-bytecode'] = translate_seq(self.data['exp'])
	def collapse(self):
		exp_bytecode = one_level_collapse(self.data['exp-bytecode'])

		fbc = []

		for i in exp_bytecode:
			fbc.append(i)

		self.data['final_bytecode'] = fbc

class TokenStmtLoop(Token):
	def __init__(self, data):
		self.data = data
	def get_translate_asts(self):
		return [self.data['cond'], self.data['body']]
	def translate_sequences(self):
		self.data['cond-bytecode'] = translate_seq(self.data['cond'])
	def collapse(self):
		cond_bytecode = one_level_collapse(self.data['cond-bytecode'])
		body_bytecode = one_level_collapse(self.data['body'])

		fbc = []

		for i in cond_bytecode:
			fbc.append(i)

		fbc.append(('flow.reljmpfalse', len(body_bytecode) + 2))

		for i in body_bytecode:
			fbc.append(i)

		self.data['final_bytecode'] = fbc

tmap = {
	'is_stmt_return': 		TokenStmtReturn,
	'is_stmt_fn': 			TokenStmtFn,
	'is_comment':       	TokenComment,
	'is_stmt_scope':    	TokenStmtScope,
	'is_stmt_type':     	TokenStmtType,
	'is_attribute':     	TokenAttribute,
	'is_invocation':    	TokenInvocation,
	'is_stmt_if':       	TokenStmtIf,
	'is_stmt_throw':    	TokenStmtThrow,
	'is_stmt_assignment':	TokenStmtAssignment,
	'is_subexpression':     TokenSubExpression,
	'is_stmt_loop':         TokenStmtLoop,
	'is_index': 			TokenIndex,
}

# TODO: remove is_index from here??
tmap_ignore = [
	'is_name', 'is_eq_or_less', 'is_number', 'is_log_or',
	'is_eq_or_greater', 'is_string', 'is_stmt_dec', 'is_less',
    'is_sub', 'is_div', 'is_not_eq', 'is_char', 
    'is_mod',
]

def translate_v2(ast, nodes_in=None):
	nodes = []

	active = []
	inactive = []

	for i in ast:
		active.append(i)

	while len(active) > 0:
		while len(active) > 0:
			item = active.pop()
			# Dynamically create instance for token so that supporting
			# logic can be associated with the JSON form of each token.
			#
			# _The `xtype` field makes this possible._
			if item['xtype'] in tmap_ignore:
				#print('ignore', item['xtype'])
				continue
			
			fac = tmap.get(item['xtype'], None)
			
			if fac is None:
				raise Exception('Unknown token type %s.' % item['xtype'])

			if fac is False:
				continue

			ioftok = tmap[item['xtype']](item)

			# Do translate of sequences to byte-code. This is
			# pre-collapse phase. The entire AST is collapsed
			# at a later point.
			#
			# _What this really means is to translate any linear
			# computation sequences into byte-code._ No control
			# flow or complex logic yet. That shall happen during
			# the collapse of the abstract syntax tree.
			#
			#if ioftok not in nodes:
			nodes.append(ioftok)

			#if item['xtype'] == 'is_subexpression':
			#	print('added subexpression at position', len(nodes) - 1)
			#	pprint.pprint(item)

			# Each custom token implementation ensures that we
			# transverse into all abstract syntax trees that will
			# require translation.
			for _ast in ioftok.get_translate_asts():
				for i in _ast:
					if item['xtype'] == 'is_stmt_assignment':
						print('------')
						pprint.pprint(i)
					inactive.append(i)

		active = inactive
		inactive = []

	print('translating sequences')
	for item in nodes:
		item.translate_sequences()

	# The collapse is designed on the fact that the
	# most upper nodes are collapsed first and then
	# the process works towards the root of the tree.
	#
	# This allows each node/token to make a one-level
	# depth collapse of any sequence of elements they
	# contain.
	#
	print('collapsing nodes', len(nodes))
	for x in range(len(nodes) - 1, -1, -1):
		node = nodes[x]
		print('collapse[%s]' % x, node.data['xtype'])
		#pprint.pprint(node.data)
		node.collapse()

	return ast

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
	if type(seq[0]) is tuple:
		# It is already in byte-code form.
		return seq

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
		elif something['xtype'] == 'is_char':
			out.append(('load.num', [ord(something['value']), 0]))
		elif something['xtype'] == 'is_make_tuple':
			args = something['args']
			
			for x in range(0, len(args)):
				args[x] = translate_seq(args[x])
				for y in args[x]:
					out.append(y)

			out.append(('tuple.pack', len(args)))
		else:
			# Unknown
			raise Exception('Compiler problem handling first item of AST assignment as %s' % something)

	#print('seq', seq)

	# A corner case where the sequence starts with negation.
	if seq[0]['xtype'] == 'is_sub':
		seq = [{ 'xtype': 'is_number', 'value': [0, 0] }] + seq

	body = Reader(seq)

	out = []

	first = body.one()

	load_something(first)

	delayed_cmp_op = None

	valid_cmp_types = [
		'is_greater',
		'is_less',
		'is_equal',
		'is_eq_or_greater',
		'is_eq_or_less',
		'is_log_or',
		'is_log_and',
		'is_log_xor',
		'is_not_eq',
	]

	def do_comparison(cmp_type):
		#print('do_comparison', cmp_type)
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
		elif cmp_type == 'is_log_or':
			out.append(('logical_or',))
		elif cmp_type == 'is_log_and':
			out.append(('logical_and',))
		elif cmp_type == 'is_log_xor':
			out.append(('logical_xor',))
		elif cmp_type == 'is_not_eq':
			out.append(('cmp_not_eq',))
		else:
			raise Exception('The comparison type was not understood.')

	#print('doing body')
	#pprint.pprint(seq)

	while body.has_more():
		a = body.one()

		if a['xtype'] == 'is_index':
			exp = translate_seq(a['exp'])
			for item in exp:
				out.append(exp)
			out.append(('load.index',))
			continue

		b = body.one()

		#print('a', a)
		#print('b', b)

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
		elif a['xtype'] == 'is_bit_or':
			out.append(('math.bit_or',))
		elif a['xtype'] == 'is_bit_and':
			out.append(('math.bit_and',))
		elif a['xtype'] == 'is_bit_xor':
			out.append(('math.bit_xor',))
		elif a['xtype'] in valid_cmp_types:
			# At this point, leave currently computed value
			# on the stack and start a new computation but
			# once end of expression or new comparison is reached
			# then do the comparison.
			#print('got valid_cmp_type', a['xtype'])

			if delayed_cmp_op is not None:
				cmp_op = delayed_cmp_op
				delayed_cmp_op = None
				do_comparison(cmp_op)

			delayed_cmp_op = a['xtype']
		else:
			print('out', out)
			raise Exception('The expected operation %s is not understood.' % a)

	# This happened because of the need to fully evaluate
	# both sides of the comparison operation. When this comparison
	# token was found the expression calculation left the currently
	# calculated left side and started on the right side and at this
	# point the left side value and right side value are on the stack.
	if delayed_cmp_op is not None:
		do_comparison(delayed_cmp_op)

	return out

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

		ast = translate_v2(inp)

		for i in ast:
			if i['xtype'] == 'is_stmt_type':
				print('TYPE %s' % i['value'])
				for q in i['body']:
					if q['xtype'] == 'is_stmt_fn':
						print('METHOD %s' % q['name'])
						for w in q['final_bytecode']:
							print(w)


if __name__ == '__main__':
	main()