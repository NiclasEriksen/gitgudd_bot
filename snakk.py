import random


KLAG = [
    "Ka du vil?",
    "Æ e altfor fjern for det her no.",
    "Kor gammale hette du ifrå sa du?",
    "Tru du snakke te feil person no, æ bry itj mæ.",
    "... ka *du* vil? :unamused:",
    [
        "Ikke ta på mæ.", "Ikke ta på mæ sa æ, æ e klam. :angry:", "Du, *seriøst*, æ e som en sel på ryggen. :frowning2:"
    ],
    ["Ikke gidd, æ e bare her for å spamme doffen bilda og vær prøvespregningssted for en annja bot.", "Seriøst, ikke gidd.", "`fåkååååf æ gidde ikke`", ":expressionless:"],
    ":middle_finger:",
    [":zzz:", "... hæ?"],
    """
```
    ______________
   /             /|
  /             / |
 /____________ /  |
|  _________  |   |____________________
| |         | |   |/        /|,       /|
| |     ..  | |   /        / /9      / |
| |  .      | |  /_______ / /9      /  |
| |_________| | |  ____ +| /9      /   |
|________++___|/|________|/9      /    |
   ________________     ,9`      /   / |
  /  -/      /-   /|  ,9        /   /| |
 /______________ //|,9         /   / | |
|       ______  ||,9          /   /  | |
|  -+  |_9366_| ||/          /   /|  | |
|_______________|/__________/   / |  | |
/////----------/|           |  /__|  | |___
|o     o  \o|  \|           |  |  |  | |
|o    \|_  ||  o|______     |  |__|  | |_____
|o \_  |   ||  o|      |    |  |  |  | /
|o /   |\  /|  o|      |    |  |  |__|/
|o             o|      |    |  |
|o-------------o|      |    |  |
|o   /\/\      o|      |    |  |
|o  / o o|     o|      |    |  |
|o / \_+_/     o|      |    |  |
|o |\     \    o|      |    |  |
|o | |+ +-|    o|      |    |  |
|o-------------o|      |    |  |
|o     /|      o|      |    | /
 \/|/|/ |/\/|/\/       |____|/
```
    """,
    """
```
 ___
|[_]|
|+ ;|
`---'
```
    """,
    ":two_hearts:",
    "Ni av ti lega anbefale at du slutte med det der.",
]


class Prat:
    used = []
    used_max = 6
    sub_list = []

    def klage(self):
        if len(self.used) >= self.used_max:
            self.used.pop(0)
        if self.sub_list:
            return self.sub_list.pop(0)

        while True:
            index = random.randint(0, len(KLAG)-1)
            if index not in self.used:
                self.used.append(index)
                break
        if type(KLAG[index]) == list:
            self.sub_list = KLAG[index].copy()
            return self.sub_list.pop(0)
        return KLAG[index]


p = Prat()
for i in range(10):
    print(p.klage())
