import pandas as pd
import subprocess

data = { 'Pure Query':[] , 'License filter':[] }

df = pd.DataFrame(data)
print(df)

#cat link.txt
for fileName in { "links.txt", "linkF.txt"}
    myOut = subprocess.Popen(['cat', fileName], link=subprocess.PIPE, stderr=subprocess.STDOUT)
    link,stderr = link.communicate()
    print(link)


    #cut -d\& -f1 link
    while (link.length > 0)
        MyOut = subprocess.Popen(['cut', '-d\&', link], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout,stderr = MyOut.communicate()
        
