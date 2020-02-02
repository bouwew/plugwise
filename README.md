# plugwise
Python library for Plugwise supporting the Adam and Anna (firmware 3.x.y)

Get data like this:

 api = Plugwise('smile', 'abcdefgh', '192.168.xyz.yz', 80)
 
 plugwise_data = api.get_plugwise_data()
 
 print(plugwise_data)
