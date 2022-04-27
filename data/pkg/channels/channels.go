package channels

import "sync"

// FanIn - сливает данные из нескольких входящих каналов в один исходящий.
//
// Если все входящие каналы закрываются, то закрывается исходящий.
func FanIn[T any](inbox ...<-chan T) <-chan T {
	out := make(chan T)

	var waitGroup sync.WaitGroup

	waitGroup.Add(len(inbox))

	go func() {
		waitGroup.Wait()
		close(out)
	}()

	for _, c := range inbox {
		c := c

		go func() {
			defer waitGroup.Done()

			for v := range c {
				out <- v
			}
		}()
	}

	return out
}

// FanOut - копирует данные из одного входящего канала в несколько исходящих.
//
// Если входящий канал закрывается, то закрываются все исходящие.
func FanOut[T any](inbox <-chan T, n int) []chan T {
	out := make([]chan T, 0, n)

	for i := 0; i < n; i++ {
		out = append(out, make(chan T))
	}

	go func() {
		var waitGroup sync.WaitGroup

		defer func() {
			waitGroup.Wait()

			for _, c := range out {
				close(c)
			}
		}()

		for value := range inbox {
			value := value

			for _, channel := range out {
				channel := channel

				waitGroup.Add(1)

				go func() {
					defer waitGroup.Done()
					channel <- value
				}()
			}
		}
	}()

	return out
}
