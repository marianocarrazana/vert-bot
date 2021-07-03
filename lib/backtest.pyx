cpdef get_price(double open, double close):
    cdef double s
    s = (open + (open + close) / 2) / 2
    return s
 
cpdef get_change(double current, double previous):
    if previous == 0:
        return 0
    elif current == previous:
        return 0
    else:
        return ((current - previous) / previous) * 100.0

cpdef get_stop_loss(double price, double stop_loss_percent):
    return price - (price*(stop_loss_percent/100))

cpdef get_funds(double funds, double diff, double fees):
    funds = funds + (funds*(diff/100))
    funds = funds - (funds*(fees/100))
    return funds