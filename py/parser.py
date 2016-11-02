#!/bin/python3
import sys
import tokenizer
import json
import pprint

def main(argv):
	print('Sedna Parser')
	if len(argv) < 2:
		print('command line syntax: <input-source> ...')
		return

	print('---start---')

	for inp in argv[1:]:
		fd = open(inp, 'rb')
		data = fd.read().decode('utf-8')
		fd.close()

		ast = tokenizer.tokenizer(data)
		print(json.dumps(ast))
		'''
			This makes easier debugging of the AST.
		'''
		#pprint.pprint(ast)

if __name__ == '__main__':
	main(sys.argv)