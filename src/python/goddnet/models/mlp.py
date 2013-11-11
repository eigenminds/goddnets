import numpy

import theano
import theano.tensor as T

from goddnet.core.model import LogisticRegression,Model,PredictorModel


class HiddenLayer(object):
    def __init__(self, rng, input, n_in, n_out, W=None, b=None,
                 activation=T.tanh):
        """
        Typical hidden layer of a MLP: units are fully-connected and have
        sigmoidal activation function. Weight matrix W is of shape (n_in,n_out)
        and the bias vector b is of shape (n_out,).

        NOTE : The nonlinearity used here is tanh

        Hidden unit activation is given by: tanh(dot(input,W) + b)

        :type rng: numpy.random.RandomState
        :param rng: a random number generator used to initialize weights

        :type input: theano.tensor.dmatrix
        :param input: a symbolic tensor of shape (n_examples, n_in)

        :type n_in: int
        :param n_in: dimensionality of input

        :type n_out: int
        :param n_out: number of hidden units

        :type activation: theano.Op or function
        :param activation: Non linearity to be applied in the hidden
                           layer
        """
        self.input = input

        # `W` is initialized with `W_values` which is uniformely sampled
        # from sqrt(-6./(n_in+n_hidden)) and sqrt(6./(n_in+n_hidden))
        # for tanh activation function
        # the output of uniform if converted using asarray to dtype
        # theano.config.floatX so that the code is runable on GPU
        # Note : optimal initialization of weights is dependent on the
        #        activation function used (among other things).
        #        For example, results presented in [Xavier10] suggest that you
        #        should use 4 times larger initial weights for sigmoid
        #        compared to tanh
        #        We have no info for other function, so we use the same as
        #        tanh.
        if W is None:
            W_values = numpy.asarray(rng.uniform(
                    low=-numpy.sqrt(6. / (n_in + n_out)),
                    high=numpy.sqrt(6. / (n_in + n_out)),
                    size=(n_in, n_out)), dtype=theano.config.floatX)
            if activation == theano.tensor.nnet.sigmoid:
                W_values *= 4

            W = theano.shared(value=W_values, name='W', borrow=True)

        if b is None:
            b_values = numpy.zeros((n_out,), dtype=theano.config.floatX)
            b = theano.shared(value=b_values, name='b', borrow=True)

        self.W = W
        self.b = b

        lin_output = T.dot(input, self.W) + self.b
        self.output = (lin_output if activation is None
                       else activation(lin_output))
        # parameters of the model
        self.params = [self.W, self.b]


class MLP(PredictorModel):

    def __init__(self, rng, input, n_in, n_hidden, n_out, L1_reg=0.0, L2_reg=0.0):

        Model.__init__(self)

        self.input=T.matrix('x')
        self.y = T.lvector('y')

        self.hidden_layer = HiddenLayer(rng=rng, input=input, n_in=n_in, n_out=n_hidden, activation=T.tanh)

        # The logistic regression layer gets as input the hidden units
        # of the hidden layer
        self.output_layer = LogisticRegression(input=self.hidden_layer.output, n_in=n_hidden, n_out=n_out)

        # L1 norm ; one regularization option is to enforce L1 norm to
        # be small
        self.L1 = abs(self.hidden_layer.W).sum() + abs(self.output_layer.W).sum()

        # square of L2 norm ; one regularization option is to enforce
        # square of L2 norm to be small
        self.L2_sqr = (self.hidden_layer.W ** 2).sum() + (self.output_layer.W ** 2).sum()

        # negative log likelihood of the MLP is given by the negative
        # log likelihood of the output of the model, computed in the
        # logistic regression layer
        self.negative_log_likelihood = self.output_layer.negative_log_likelihood + L1_reg*self.L1 + L2_reg*self.L2_sqr
        # same holds for the function computing the number of errors
        self.errors = self.output_layer.errors

        # the parameters of the model are the parameters of the two layer it is
        # made out of
        self.params = [self.hidden_layer.params, self.output_layer.params]

        self.cost = lambda: self.negative_log_likelihood

        learning_rate = T.scalar('learning_rate')  # learning rate to use

        self.train_model = theano.function(inputs=[self.input, self.y, theano.Param(learning_rate, default=0.13)],
                                           outputs=self.cost(),
                                           updates=self.get_updates(learning_rate),
                                           givens={})

        self.predict = theano.function(inputs=[self.input], outputs=self.output_layer.y_pred)

    def train(self, data, learning_rate=.13):
        train_set_x = numpy.array([x[0] for x in data])
        train_set_y = numpy.array([x[1] for x in data])
        c = self.train_model(train_set_x,train_set_y,learning_rate=learning_rate)
        return c


