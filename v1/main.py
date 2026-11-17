# -*- coding: utf-8 -*-
"""
Created on Tue Apr 28 21:08:39 2020

@author: Josafath
"""
from tkinter import messagebox
from tkinter import *
import random
import sys
root = Tk()
#Global counter for the game
root.user_wins = 0
root.cpu_wins = 0

def check_winner(user_points,cpu_points):
    if user_points == 10:
        r.set("You Won!")
        wins_person.set("")
        wins_cpu.set("")
        root.user_wins = root.cpu_wins = 0
        messagebox.showinfo("Game Finished", "You have won. Congratulations! :)")
        continue_game = messagebox.askyesno('Again?', 'Do you wanna try again?')
        if not continue_game:
            messagebox.showinfo(':(', "Bye, my friend")
            root.destroy()

    elif cpu_points == 10:
        r.set("You Losed!")
        wins_person.set("")
        wins_cpu.set("")
        root.user_wins = root.cpu_wins = 0
        messagebox.showinfo("Game Finished", "You have losed. Sorry. :(")
        continue_game = messagebox.askyesno('Again?', 'Do you wanna try again?')

        if not continue_game:
            messagebox.showinfo(':(', "Bye, my friend")
            root.destroy()

    else:
        pass

def papel():
    choice = random.choice(['Piedra','Tijeras','Papel'])
    if choice == 'Piedra':
        r.set("¡You Win!")
        root.user_wins+=1
        wins_person.set("User Wins: " + str(root.user_wins))
        check_winner(root.user_wins,root.cpu_wins)

    elif choice == 'Tijeras':
        r.set("You lose ):")
        root.cpu_wins += 1
        wins_cpu.set("Cpu Wins: " + str(root.cpu_wins))
        check_winner(root.user_wins, root.cpu_wins)

    else:
        r.set("Draw!!")
        
def tijeras():

    choice = random.choice(['Piedra','Tijeras','Papel'])
    if choice == 'Piedra':
        r.set("You lose :(")
        root.cpu_wins += 1
        wins_cpu.set("Cpu Wins: " + str(root.cpu_wins))
        check_winner(root.user_wins, root.cpu_wins)

        
    elif choice == 'Papel':
        r.set("¡You Win!")
        root.user_wins += 1
        wins_person.set("User Wins: " + str(root.user_wins))
        check_winner(root.user_wins, root.cpu_wins)

    else:
        r.set("Draw!!")

def piedra():
    choice = random.choice(["Piedra","Tijeras","Papel"])
    if choice == "Tijeras":
        r.set("¡You Winn!")
        root.user_wins += 1
        wins_person.set("User Wins: " + str(root.user_wins))
        check_winner(root.user_wins, root.cpu_wins)

    elif choice == "Papel":
        r.set("You lose :(")
        root.cpu_wins += 1
        wins_cpu.set("Cpu Wins: " + str(root.cpu_wins))
        check_winner(root.user_wins, root.cpu_wins)

    else:
        r.set("Draw!!")


root.title("Los geth's!")
wins_person = StringVar()
wins_cpu = StringVar()
r = StringVar()
Piedra = PhotoImage(file=sys.path[0]+"\Images\Rock.png")
Papel = PhotoImage(file=sys.path[0]+"\Images\Paper.png")
Tijeras = PhotoImage(file=sys.path[0]+"\Images\Scissors.png")
boton1 = Button(root,text="paper",image = Piedra,command=papel)
boton1.grid(padx = 15,pady = 5,row =1 ,column=1)
boton2 = Button(root,text="cissors",image = Papel,command=tijeras)
boton2.grid(padx = 15,pady = 5,row =1 ,column=2)
boton3 = Button(root,text="rock",image = Tijeras,command=piedra)
boton3.grid(padx = 15, pady =5,row =1 ,column=3)

Label(root,textvariable= r,
      font =('Permanent Marker', 15)).grid(padx = 10,pady = 10,row= 2,column = 2)
Label(root,textvariable= wins_person,
      font =('Permanent Market', 15)).grid(padx = 10,pady = 10,row= 2,column = 1)
Label(root,textvariable= wins_cpu,
      font =('Permanent Market', 15)).grid(padx = 10,pady = 10,row= 2,column = 3)

root.mainloop()