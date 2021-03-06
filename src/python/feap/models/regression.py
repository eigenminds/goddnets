import numpy
import theano
import theano.tensor as T
from feap.core.model import PredictorModel

class LinearRegression(PredictorModel):
    """
    Multivariate linear regression
    """
    def __init__(self, in_size, out_size):

        PredictorModel.__init__(self)

        self.input=T.matrix('x')
        self.y = T.matrix('y')

        # Init weights
        self.W = theano.shared(value=numpy.zeros((in_size, out_size), dtype=theano.config.floatX), name='W', borrow=True)

        # Init bias
        self.b = theano.shared(value=numpy.zeros((out_size,), dtype=theano.config.floatX), name='b', borrow=True)

        self.y_pred = self.get_prediction(self.input)

        # model parameters
        self.params = [self.W, self.b]

        learning_rate = T.scalar('learning_rate')  # learning rate to use

        self.cost = lambda: self.negative_log_likelihood()
        self.train_model = theano.function(inputs=[self.input,self.y,theano.Param(learning_rate, default=0.13)],
                                           outputs=self.cost(),
                                           updates=self.get_updates(learning_rate),
                                           givens={})
        self.pred_input = T.vector('pred_input')
        self.predict = theano.function(inputs=[self.pred_input], outputs=self.get_prediction(self.pred_input))

    def get_prediction(self, x):
        return T.dot(x, self.W) + self.b

    def errors(self, y):
        super(LinearRegression,self).errors(y)
        return T.mean(T.sqr(self.y_pred - y))

    def train(self, data, learning_rate=.13):
        train_set_x = numpy.array([x[0] for x in data])
        train_set_y = numpy.array([x[1] for x in data])
        cost = self.train_model(train_set_x,train_set_y,learning_rate=learning_rate)
        return cost

    def negative_log_likelihood(self):
        return T.mean(T.sqr(self.y_pred - self.y))


class LogisticRegression(PredictorModel):
    """
    Multiclass logistic regression
    """
    def __init__(self, in_size, out_size, input=None):
        """
        input = input examples (symbol)
        in_size = size of input
        out_size = size of output
        """
        super(LogisticRegression,self).__init__()

        if input is None:
            self.input=T.matrix('x')
        else:
            self.input=input
        self.y = T.lvector('y')

        # Init weights
        self.W = theano.shared(value=numpy.zeros((in_size, out_size), dtype=theano.config.floatX),
            name='W', borrow=True)

        # Init bias
        self.b = theano.shared(value=numpy.zeros((out_size,), dtype=theano.config.floatX),
            name='b', borrow=True)

        # Class probabilities - softmax of input*weights+bias
        self.p_y_given_x = self.get_class_probabilities(self.input)

        # Class prediction - maximum probability
        self.y_pred = self.get_prediction(self.p_y_given_x)

        # model parameters
        self.params.extend([self.W, self.b])

        learning_rate = T.scalar('learning_rate')  # learning rate to use

        self.cost=self.negative_log_likelihood
        self.train_model = theano.function(inputs=[self.input,self.y,theano.Param(learning_rate, default=0.13)],
            outputs=self.cost(),
            updates=self.get_updates(learning_rate),
        )
        self.pred_input = T.vector('pred_input')
        self.predict = theano.function(inputs=[self.pred_input],
            outputs=self.get_prediction(self.get_class_probabilities(self.pred_input)),
        )
        # compiling a Theano function that computes the mistakes that are made by
        # the model on a minibatch
        self.test_model = theano.function(inputs=[self.input,self.y],
            outputs=self.errors(self.y),
        )

    def get_class_probabilities(self, x):
        return T.nnet.softmax(T.dot(x, self.W) + self.b)

    def get_prediction(self, x):
        return T.argmax(x,axis=1)

    def errors(self, y):
        super(LogisticRegression,self).errors(y)

        # check if y is of the correct datatype
        if not y.dtype.startswith('int'):
            raise NotImplementedError()
        return T.mean(T.neq(self.y_pred, y))

    def train(self, data, learning_rate=.13):
        train_set_x = numpy.array([x[0] for x in data])
        train_set_y = numpy.array([x[1] for x in data])
        cost = self.train_model(train_set_x,train_set_y,learning_rate=learning_rate)
        return cost

    def negative_log_likelihood(self):
        return -T.mean(T.log(self.p_y_given_x)[T.arange(self.y.shape[0]), self.y])


class ComplexLinearRegression(PredictorModel):

    def __init__(self, in_size, out_size):

        PredictorModel.__init__(self)

        self.input=T.zmatrix('X')
        self.y = T.zmatrix('y')

        # Init weights
        self.W = theano.shared(value=numpy.zeros((in_size, out_size), dtype=numpy.complex128), name='W', borrow=True)

        # Init bias
        self.b = theano.shared(value=numpy.zeros((out_size,), dtype=numpy.complex128), name='b', borrow=True)

        self.y_pred = self.get_prediction(self.input)

        # model parameters
        self.params = [self.W, self.b]

        learning_rate = T.scalar('learning_rate')  # learning rate to use

        self.cost = lambda: self.negative_log_likelihood()
        self.train_model = theano.function(inputs=[self.input,self.y,theano.Param(learning_rate, default=0.13)],
                                           outputs=self.cost(),
                                           updates=self.get_updates(learning_rate),
                                           givens={})
        self.pred_input = T.vector('pred_input')
        self.predict = theano.function(inputs=[self.pred_input], outputs=self.get_prediction(self.pred_input))

    def get_prediction(self, x):
        return T.dot(x, self.W) + self.b

    def negative_log_likelihood(self):
        return T.mean( T.real((self.y_pred - self.y) * T.conj(self.y_pred - self.y)) )

    def get_updates(self, learning_rate):

        #specify the expression used to compute the weight update, with complex gradient descent
        dW = self.W + learning_rate*self.negative_log_likelihood()*T.conj(self.input)
        gparams = T.grad(self.cost(), self.params)
        # generate the list of updates
        updates = []
        for param, gparam in zip(self.params, gparams):
            updates.append((param, param - learning_rate * gparam))
        return updates