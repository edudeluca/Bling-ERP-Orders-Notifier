from notifypy import Notify

def getNewOrderNotification(listOfNewOrders : list):
    notify_new = Notify()
    notify_new.application_name = 'Monitor Bling'
    notify_new.title = 'Nova Venda'
    notify_new.message = ', '.join([str(i) for i in listOfNewOrders])

    # notify_new.audio = (os.path.join(resources,'notify_new.wav'))

    notify_new.send(block=False)

def getLateOrderNotification(listOfLateOrders : list):
    notify_old = Notify()
    notify_old.application_name = 'Monitor Bling'
    notify_old.title = 'Vendas em Atraso'
    notify_old.message = ', '.join([str(i) for i in listOfLateOrders])

    # notify_old.audio = (os.path.join(resources,'notify_old.wav'))

    notify_old.send(block=False)