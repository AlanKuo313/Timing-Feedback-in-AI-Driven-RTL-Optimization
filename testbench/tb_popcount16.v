`timescale 1ns/1ps
module tb_popcount16;
    reg clk=0;
    always #5 clk=~clk;
    reg [15:0] bits=0, prev_bits=0;
    wire [4:0] count;
    reg [4:0] expected;
    integer cycle=0, k, i;
    popcount16 dut(.clk(clk), .bits(bits), .count(count));
    always @(posedge clk) begin
        if(cycle>0) begin
            expected=0;
            for(i=0;i<16;i=i+1) expected=expected+prev_bits[i];
            #1;
            if(count !== expected) $fatal(1,"popcount mismatch cycle %0d",cycle);
        end
        prev_bits=bits; cycle=cycle+1;
    end
    initial begin
        for(k=0;k<250;k=k+1) begin
            @(negedge clk);
            bits=(k%5==0)?16'hffff:$random;
        end
        @(negedge clk);
        $display("PASS: popcount16 %0d vectors",cycle-1);
        $finish;
    end
endmodule
