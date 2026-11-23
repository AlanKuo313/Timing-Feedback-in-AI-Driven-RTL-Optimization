`timescale 1ns/1ps
module tb_adder16;
    reg clk = 0;
    always #5 clk = ~clk;
    reg [15:0] a = 0, b = 0;
    wire [16:0] sum;
    reg [15:0] prev_a = 0, prev_b = 0;
    integer cycle = 0;
    reg [16:0] expected;
    adder16 dut(.clk(clk), .a(a), .b(b), .sum(sum));
    always @(posedge clk) begin
        if (cycle > 0) begin
            expected = {1'b0, prev_a} + {1'b0, prev_b};
            #1;
            if (sum !== expected) $fatal(1, "Adder mismatch cycle %0d: got %h expected %h", cycle, sum, expected);
        end
        prev_a = a;
        prev_b = b;
        cycle = cycle + 1;
    end
    integer k;
    initial begin
        for (k=0; k<250; k=k+1) begin
            @(negedge clk);
            a = $random;
            b = $random;
        end
        @(negedge clk);
        $display("PASS: adder16 %0d vectors", cycle-1);
        $finish;
    end
endmodule
