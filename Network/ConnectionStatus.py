class ConnectionStatus:
    def __init__(self) -> None:
        self.sending = False
        self.receiving = False
        self.sending_timedout = False
        self.receiving_timedout = False
        self.sending_err = None
        self.receiving_err = None

    def set_sending(self, state: bool):
        self.sending = state

    def set_receiving(self, state: bool):
        self.receiving = state

    def set_sendingtimedout(self, state: bool):
        self.sending_timedout = state

    def set_receivingtimedout(self, state: bool):
        self.receiving_timedout = state
    
    def set_receiving_err(self, exception):
        self.receiving_err = exception
    
    def set_sending_err(self, exception):
        self.sending_err = exception

    # TODO: implement status report on the UI